"""Sarvam client singleton + the supported-language set.

Only languages that have ALL THREE of STT + Translate + TTS are offered, so every
pair works both ways with text *and* voice. That intersection is exactly the 11
languages Sarvam TTS (bulbul) supports.
"""
from functools import lru_cache

from .config import get_settings

# code -> (English name, native name). Order = display order in the dropdowns.
LANGUAGES: dict[str, tuple[str, str]] = {
    "hi-IN": ("Hindi", "हिन्दी"),
    "bn-IN": ("Bengali", "বাংলা"),
    "ta-IN": ("Tamil", "தமிழ்"),
    "te-IN": ("Telugu", "తెలుగు"),
    "kn-IN": ("Kannada", "ಕನ್ನಡ"),
    "ml-IN": ("Malayalam", "മലയാളം"),
    "mr-IN": ("Marathi", "मराठी"),
    "gu-IN": ("Gujarati", "ગુજરાતી"),
    "pa-IN": ("Punjabi", "ਪੰਜਾਬੀ"),
    "od-IN": ("Odia", "ଓଡ଼ିଆ"),
    "en-IN": ("English", "English"),
}

SUPPORTED_CODES = frozenset(LANGUAGES)


def language_list() -> list[dict[str, str]]:
    """Shape the frontend consumes from GET /api/languages."""
    return [
        {"code": code, "name": name, "native": native}
        for code, (name, native) in LANGUAGES.items()
    ]


@lru_cache
def get_client():
    """Lazily build the SarvamAI client so STUB_MODE never imports/needs the SDK."""
    from sarvamai import SarvamAI  # imported here so stub mode has no hard dependency

    return SarvamAI(api_subscription_key=get_settings().sarvam_api_key)
