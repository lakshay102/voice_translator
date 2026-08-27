"""Environment-backed settings. Fail fast if the API key is missing."""
import os
from functools import lru_cache


class Settings:
    def __init__(self) -> None:
        self.stub_mode: bool = os.environ.get("STUB_MODE", "0").strip() in {"1", "true", "True"}
        self.debug: bool = os.environ.get("DEBUG", "0").strip() in {"1", "true", "True"}

        self.sarvam_api_key: str = os.environ.get("SARVAM_API_KEY", "").strip()
        if not self.sarvam_api_key and not self.stub_mode:
            raise RuntimeError(
                "SARVAM_API_KEY is not set. Copy .env.example to .env and add your key, "
                "or run with STUB_MODE=1 to exercise the frontend contract without Sarvam."
            )

        self.stt_model: str = os.environ.get("SARVAM_STT_MODEL", "saaras:v3").strip()
        self.translate_model: str = os.environ.get("SARVAM_TRANSLATE_MODEL", "mayura:v1").strip()
        self.translate_mode: str = os.environ.get("SARVAM_TRANSLATE_MODE", "modern-colloquial").strip()
        self.tts_model: str = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v2").strip()

        # bulbul speakers are language-agnostic (they speak whatever language_code
        # you pass), so one voice covers all 11 languages. Override per-language
        # with SARVAM_TTS_SPEAKER_<CODE>, e.g. SARVAM_TTS_SPEAKER_TA=vidya.
        self.tts_speaker_default: str = os.environ.get("SARVAM_TTS_SPEAKER", "anushka").strip()
        self.tts_sample_rate: int = int(os.environ.get("SARVAM_TTS_SAMPLE_RATE", "22050"))

    def tts_speaker_for(self, lang_code: str) -> str:
        key = "SARVAM_TTS_SPEAKER_" + lang_code.split("-")[0].upper()
        return os.environ.get(key, self.tts_speaker_default).strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
