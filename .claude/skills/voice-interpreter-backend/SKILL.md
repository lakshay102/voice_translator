---
name: voice-interpreter-backend
description: The FastAPI backend contract and build conventions for Bhasha Bridge — the single /api/translate-turn endpoint that chains Sarvam STT → Translate → TTS. Use when scaffolding, extending, or debugging the backend, wiring env config, or deciding request/response shapes.
metadata:
  type: project
---

# Bhasha Bridge — Backend

**Why:** v1 has a strict scope and a next-day deadline. One endpoint, one shape, direction is a flag. Resist adding routes, a DB, or auth.
**How to apply:** Follow the contract below verbatim so the frontend never has to change when the pipeline is wired in.

Depends on: [[sarvam-api]] for all language codes, model names, and call signatures.

## The one endpoint

```
POST /api/translate-turn
Content-Type: multipart/form-data

fields:
  audio      : file  (browser MediaRecorder blob, audio/webm;codecs=opus)
  direction  : str   ("ta_to_hi" | "hi_to_ta")

200 response (application/json):
{
  "source_text":     "<transcript in the speaker's language>",
  "translated_text": "<translation in the listener's language>",
  "audio_base64":    "<base64 mp3, no data: prefix>"
}

soft-failure response (HTTP 422):
{ "error": "no_speech" | "stt_failed" | "translate_failed" | "tts_failed",
  "detail": "<short human string>" }
```

No other endpoints. A `GET /` or `GET /health` returning `{"ok": true}` is fine. Static frontend is served by the same app.

## Project layout

```
sarvam_ai/
├── app/
│   ├── main.py          # FastAPI app, CORS, static mount, the one route
│   ├── pipeline.py      # transcribe() -> translate() -> synthesize(), pure functions
│   ├── sarvam.py        # SarvamAI client singleton + LANGS map
│   └── config.py        # env loading, fail-fast on missing SARVAM_API_KEY
├── static/
│   └── index.html       # the whole frontend (see voice-interpreter-frontend)
├── samples/             # pre-recorded voice notes for testing without a mic
├── .env.example
├── requirements.txt
└── docs/
```

## config.py

```python
import os
from functools import lru_cache

class Settings:
    def __init__(self):
        self.sarvam_api_key = os.environ.get("SARVAM_API_KEY", "").strip()
        if not self.sarvam_api_key:
            raise RuntimeError(
                "SARVAM_API_KEY is not set. Copy .env.example to .env and add your key."
            )
        self.stt_model       = os.environ.get("SARVAM_STT_MODEL", "saaras:v3")
        self.translate_model  = os.environ.get("SARVAM_TRANSLATE_MODEL", "mayura:v1")
        self.tts_model        = os.environ.get("SARVAM_TTS_MODEL", "bulbul:v2")
        self.tts_speaker_hi   = os.environ.get("SARVAM_TTS_SPEAKER_HI", "anushka")
        self.tts_speaker_ta   = os.environ.get("SARVAM_TTS_SPEAKER_TA", "anushka")

@lru_cache
def get_settings() -> "Settings":
    return Settings()
```

Load `.env` early (e.g. `python-dotenv` `load_dotenv()` at the top of `main.py`) so `uvicorn app.main:app` works without exporting vars.

## pipeline.py — keep the three steps separate and pure

```python
def transcribe(audio_bytes: bytes, filename: str, lang_code: str) -> str: ...
def translate(text: str, src: str, tgt: str) -> str: ...
def synthesize(text: str, tgt_lang: str) -> str:   # returns base64 mp3
```

- Each raises a typed exception (`SttError`, `TranslateError`, `TtsError`) on failure.
- The route catches those and maps to the 422 `error` codes above.
- An empty/whitespace transcript from `transcribe()` → raise `SttError("no_speech")` so the route returns `{"error": "no_speech"}`.
- Do **not** persist anything. No files written except optionally a debug copy of the last upload under `samples/_last.webm` when `DEBUG=1`.

## The route (shape it like this)

```python
@app.post("/api/translate-turn")
async def translate_turn(audio: UploadFile = File(...), direction: str = Form(...)):
    if direction not in LANGS:
        raise HTTPException(400, "direction must be ta_to_hi or hi_to_ta")
    cfg = LANGS[direction]
    data = await audio.read()
    if len(data) < 1500:                     # ~empty recording
        return JSONResponse(status_code=422, content={"error": "no_speech",
            "detail": "Recording was empty or too short."})
    try:
        source_text = transcribe(data, audio.filename or "clip.webm", cfg["stt"])
    except SttError as e:
        return _soft(422, "no_speech" if str(e) == "no_speech" else "stt_failed", e)
    try:
        translated_text = translate(source_text, cfg["src"], cfg["tgt"])
    except TranslateError as e:
        return _soft(422, "translate_failed", e)
    try:
        audio_base64 = synthesize(translated_text, cfg["tgt"])
    except TtsError as e:
        return _soft(422, "tts_failed", e)
    return {"source_text": source_text,
            "translated_text": translated_text,
            "audio_base64": audio_base64}
```

## CORS / serving

- For local dev where frontend and backend are the same origin (served from `/static` or mounted at `/`), CORS isn't needed.
- If you run the HTML from a different port during dev, add `CORSMiddleware` with `allow_origins=["*"]` for v1 only.
- Mount static: `app.mount("/", StaticFiles(directory="static", html=True), name="static")` **after** defining `/api/...` routes.

## Build order (matches docs/BUILD_PHASES.md)

1. **Stub first.** Route returns a canned `{source_text, translated_text, audio_base64}` (base64 of a short silent/beep mp3). Confirm the frontend round-trips against this before any Sarvam call.
2. Wire `transcribe()` → return `source_text` real, keep translate/tts stubbed.
3. Wire `translate()`.
4. Wire `synthesize()`.
5. Add the 422 soft-failure handling and the `< 1500 bytes` guard.

## requirements.txt

```
fastapi
uvicorn[standard]
python-multipart
python-dotenv
sarvamai
```

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`--host 0.0.0.0` so a phone on the same Wi-Fi can reach `http://<laptop-ip>:8000`. Note: mobile browsers block `getUserMedia` on non-HTTPS origins **except** `localhost` — for on-phone testing you need HTTPS (use a tunnel like the platform's, or deploy). See docs/BUILD_PHASES.md deployment section.

## Explicitly NOT in the backend for v1

- No MongoDB / any database. Conversation history lives in browser memory.
- No second endpoint, no language selector, no auto-detect (`direction` tells you everything).
- No streaming / websockets.
- No user accounts / sessions / rate limiting of our own.
