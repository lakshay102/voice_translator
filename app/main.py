"""Bhasha Bridge — FastAPI app. One translate endpoint + a language list, serves the static frontend."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # so `uvicorn app.main:app` works without exporting vars

from fastapi import FastAPI, File, Form, UploadFile  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from .config import get_settings  # noqa: E402
from .pipeline import (  # noqa: E402
    NoSpeechError,
    PipelineError,
    synthesize,
    transcribe,
    translate,
)
from .sarvam import SUPPORTED_CODES, language_list  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
SAMPLES_DIR = BASE_DIR / "samples"

settings = get_settings()  # fail fast on missing key (unless STUB_MODE)

app = FastAPI(title="Bhasha Bridge", version="1.0.0")

# Min bytes for a recording we'll bother sending to STT. Smaller = accidental tap / silence.
MIN_AUDIO_BYTES = 1500


def _soft(code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=422, content={"error": code, "detail": detail})


@app.get("/health")
def health() -> dict:
    return {"ok": True, "stub_mode": settings.stub_mode}


@app.get("/api/languages")
def languages() -> dict:
    """Single source of truth for the dropdowns. Every code here has STT+Translate+TTS."""
    return {"languages": language_list()}


@app.post("/api/translate-turn", response_model=None)
async def translate_turn(
    audio: UploadFile = File(...),
    source_lang: str = Form(...),
    target_lang: str = Form(...),
):
    if source_lang not in SUPPORTED_CODES or target_lang not in SUPPORTED_CODES:
        return JSONResponse(
            status_code=400,
            content={"error": "bad_language",
                     "detail": f"source_lang/target_lang must be one of {sorted(SUPPORTED_CODES)}"},
        )
    if source_lang == target_lang:
        return JSONResponse(
            status_code=400,
            content={"error": "same_language",
                     "detail": "source_lang and target_lang must differ"},
        )

    data = await audio.read()
    if len(data) < MIN_AUDIO_BYTES:
        return _soft("no_speech", "Recording was empty or too short.")

    if settings.debug:
        try:
            SAMPLES_DIR.mkdir(exist_ok=True)
            ext = os.path.splitext(audio.filename or "")[1] or ".webm"
            (SAMPLES_DIR / f"_last{ext}").write_bytes(data)
        except OSError:
            pass

    filename = audio.filename or "clip.webm"

    try:
        source_text = transcribe(data, filename, source_lang)
    except NoSpeechError:
        return _soft("no_speech", "Didn't catch any speech. Try again with a short phrase.")
    except PipelineError as exc:
        return _soft("stt_failed", str(exc))

    try:
        translated_text = translate(source_text, source_lang, target_lang)
    except PipelineError as exc:
        return _soft("translate_failed", str(exc))

    try:
        audio_base64 = synthesize(translated_text, target_lang)
    except PipelineError as exc:
        return _soft("tts_failed", str(exc))

    return {
        "source_text": source_text,
        "translated_text": translated_text,
        "audio_base64": audio_base64,
    }


# Static frontend LAST, so it doesn't shadow /api routes. html=True serves index.html at "/".
if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
