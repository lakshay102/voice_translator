"""The three pipeline steps: transcribe -> translate -> synthesize.

Each function is pure-ish (no shared state), and raises a typed error on failure.
The route maps those errors to the 422 soft-failure contract.
"""
from __future__ import annotations

import base64
import io
import os
import tempfile

from .config import get_settings
from .sarvam import get_client


class PipelineError(Exception):
    """Base for a step failure. `code` matches the API's `error` field."""

    code = "pipeline_failed"


class SttError(PipelineError):
    code = "stt_failed"


class NoSpeechError(SttError):
    code = "no_speech"


class TranslateError(PipelineError):
    code = "translate_failed"


class TtsError(PipelineError):
    code = "tts_failed"


def _attr(obj, name: str):
    """Read `name` from a pydantic model or a plain dict response."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


# --------------------------------------------------------------------------- STT
def transcribe(audio_bytes: bytes, filename: str, lang_code: str) -> str:
    settings = get_settings()

    if settings.stub_mode:
        return "[stub transcript]"

    suffix = os.path.splitext(filename)[1] or ".webm"
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        with open(tmp_path, "rb") as fh:
            resp = get_client().speech_to_text.transcribe(
                file=fh,
                model=settings.stt_model,
                language_code=lang_code,
            )
    except Exception as exc:  # network, auth, bad audio, SDK error
        raise SttError(f"speech-to-text call failed: {exc}") from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

    transcript = (_attr(resp, "transcript") or "").strip()
    if not transcript:
        raise NoSpeechError("empty transcript")
    return transcript


# --------------------------------------------------------------------- Translate
def translate(text: str, src: str, tgt: str) -> str:
    settings = get_settings()

    if settings.stub_mode:
        return f"[stub translation {src}->{tgt}] {text}"

    try:
        resp = get_client().text.translate(
            input=text,
            source_language_code=src,
            target_language_code=tgt,
            model=settings.translate_model,
            mode=settings.translate_mode,
        )
    except Exception as exc:
        raise TranslateError(f"translate call failed: {exc}") from exc

    translated = (_attr(resp, "translated_text") or "").strip()
    if not translated:
        raise TranslateError("empty translation")
    return translated


# --------------------------------------------------------------------------- TTS
def synthesize(text: str, tgt_lang: str) -> str:
    """Return base64-encoded mp3 (no data: prefix)."""
    settings = get_settings()

    if settings.stub_mode:
        return _SILENT_MP3_B64

    speaker = settings.tts_speaker_for(tgt_lang)
    try:
        resp = get_client().text_to_speech.convert(
            text=text,
            language_code=tgt_lang,  # SDK param is `language_code` (it's the output language)
            model=settings.tts_model,
            speaker=speaker,
            speech_sample_rate=settings.tts_sample_rate,
            output_audio_codec="mp3",
        )
    except Exception as exc:
        raise TtsError(f"text-to-speech call failed: {exc}") from exc

    audios = _attr(resp, "audios") or []
    if not audios:
        raise TtsError("no audio returned")
    # `audios` may be split into chunks for long text; concatenate the decoded bytes.
    try:
        raw = b"".join(base64.b64decode(chunk) for chunk in audios)
    except Exception as exc:
        raise TtsError(f"could not decode returned audio: {exc}") from exc
    return base64.b64encode(raw).decode("ascii")


# A ~0.4s silent MP3 (real libmp3lame output). Used only in STUB_MODE so the
# frontend can exercise the full round-trip, including <audio> playback, with no
# Sarvam calls.
_SILENT_MP3_B64 = (
    "SUQzBAAAAAAAIlRTU0UAAAAOAAADTGF2ZjYyLjMuMTAwAAAAAAAAAAAAAAD/83DAAAAAAAAAAAAASW5mbwAAAA8AAAASAAACigBRUVFRUVxcXFxcXGZmZmZmcHBwcHBwenp6enqFhYWFhYWPj4+Pj5mZmZmZmaOjo6Ojrq6urq6uuLi4uLi4wsLCwsLMzMzMzMzX19fX1+Hh4eHh4evr6+vr9fX19fX1//////8AAAAATGF2YzYyLjExAAAAAAAAAAAAAAAAJAPMAAAAAAAAAooAnxCfAAAAAAAAAAAAAAAAAP/zEMQAAAADSAAAAABMQU1FMy4xMDBVVVVV//MQxA0AAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDEGgAAA0gAAAAAVVVVVVVVVVVVVVVVVf/zEMQnAAADSAAAAABVVVVVVVVVVVVVVVVV//MQxDQAAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDEQQAAA0gAAAAAVVVVVVVVVVVVVVVVVf/zEMROAAADSAAAAABVVVVVVVVVVVVVVVVV//MQxFsAAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDEaAAAA0gAAAAAVVVVVVVVVVVVVVVVVf/zEMR1AAADSAAAAABVVVVVVVVVVVVVVVVV//MQxIIAAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDEjwAAA0gAAAAAVVVVVVVVVVVVVVVVVf/zEMScAAADSAAAAABVVVVVVVVVVVVVVVVV//MQxKkAAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDEtgAAA0gAAAAAVVVVVVVVVVVVVVVVVf/zEMTDAAADSAAAAABVVVVVVVVVVVVVVVVV//MQxNAAAANIAAAAAFVVVVVVVVVVVVVVVVX/8xDE3QAAA0gAAAAAVVVVVVVVVVVVVVVVVQ=="
)
