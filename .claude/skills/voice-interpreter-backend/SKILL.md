---
name: voice-interpreter-backend
description: The FastAPI backend contract and conventions for Bhasha Bridge — POST /api/translate-turn (Sarvam STT → Translate → TTS) plus GET /api/languages. Use when extending or debugging the backend, wiring env config, or changing request/response shapes.
metadata:
  type: project
---

# Bhasha Bridge — Backend

**Why:** v1 has a strict scope and a next-day deadline. Two endpoints, one pipeline, the
language pair is two form fields. No DB, no auth, no extra routes.
**How to apply:** Keep the contract below stable so the frontend never has to change.

Depends on: [[sarvam-api]] for language codes, model names, and call signatures
(verified against `sarvamai==0.1.31`).

## Endpoints

### `GET /api/languages` — dropdown source of truth
```json
{ "languages": [ { "code": "hi-IN", "name": "Hindi", "native": "हिन्दी" }, … ] }
```
Exactly the 11 languages with STT + Translate + TTS. Defined once in `app/sarvam.py`.

### `POST /api/translate-turn`
```
Content-Type: multipart/form-data
  audio        : file    MediaRecorder blob (audio/webm;codecs=opus, or audio/mp4 on iOS)
  source_lang  : str     one of the 11 codes  (speaker's language)
  target_lang  : str     one of the 11 codes  (listener's language, must differ)

200 application/json
  { "source_text": str, "translated_text": str, "audio_base64": str }   # base64 mp3, no data: prefix

422 application/json   (soft failure — UI shows a retry message)
  { "error": "no_speech" | "stt_failed" | "translate_failed" | "tts_failed", "detail": str }

400 application/json
  { "error": "bad_language" | "same_language", "detail": str }
```

### `GET /health` → `{"ok": true, "stub_mode": bool}`

No other endpoints. Static frontend served by the same app.

## Project layout

```
sarvam_ai/
├── app/
│   ├── main.py      FastAPI app · load_dotenv · the routes · StaticFiles mount (LAST)
│   ├── pipeline.py  transcribe() / translate() / synthesize() — pure, typed errors, STUB_MODE
│   ├── sarvam.py    SarvamAI client singleton · LANGUAGES (11) · SUPPORTED_CODES · language_list()
│   └── config.py    Settings, fail-fast on missing SARVAM_API_KEY · model/speaker/rate env · tts_speaker_for()
├── static/index.html
├── samples/         pre-recorded clips for mic-less testing
├── .env / .env.example
├── requirements.txt
└── .claude/launch.json   uvicorn --host 0.0.0.0 --port 8000
```

## config.py essentials

- Reads `.env` via `python-dotenv` `load_dotenv()` at the top of `main.py`.
- `STUB_MODE=1` — pipeline returns canned text + a real silent MP3, never imports the SDK,
  and `SARVAM_API_KEY` becomes optional. Used for offline frontend work.
- Fail fast: no key and not stub → `RuntimeError` at startup.
- Env overrides: `SARVAM_STT_MODEL` (`saaras:v3`), `SARVAM_TRANSLATE_MODEL` (`mayura:v1`),
  `SARVAM_TRANSLATE_MODE` (`modern-colloquial`), `SARVAM_TTS_MODEL` (`bulbul:v2`),
  `SARVAM_TTS_SPEAKER` (`anushka`), `SARVAM_TTS_SPEAKER_<CODE>` per-language,
  `SARVAM_TTS_SAMPLE_RATE` (`22050`).

## pipeline.py — three pure steps, typed errors

```python
transcribe(audio_bytes: bytes, filename: str, lang_code: str) -> str        # -> .transcript
translate(text: str, src: str, tgt: str) -> str                             # -> .translated_text
synthesize(text: str, tgt_lang: str) -> str                                 # -> base64 mp3
```

- Error hierarchy: `PipelineError` ← `SttError` ← `NoSpeechError`; `TranslateError`; `TtsError`.
  Each carries a `.code` matching the API `error` field.
- Empty/whitespace transcript → `NoSpeechError`.
- `synthesize` concatenates `resp.audios` (it's an array; long text splits into chunks)
  then re-encodes to one base64 string. Speaker from `settings.tts_speaker_for(tgt_lang)`.
- TTS SDK param is **`language_code`**, not `target_language_code`.
- `_attr()` helper reads a field from either a pydantic model or a dict, so response
  shape changes don't break it.
- No persistence. `DEBUG=1` optionally writes the last upload to `samples/_last.<ext>`.

## The route

```python
@app.post("/api/translate-turn", response_model=None)   # response_model=None: return type is a union
async def translate_turn(audio: UploadFile = File(...),
                         source_lang: str = Form(...),
                         target_lang: str = Form(...)):
    if source_lang not in SUPPORTED_CODES or target_lang not in SUPPORTED_CODES:
        return JSONResponse(400, {"error": "bad_language", ...})
    if source_lang == target_lang:
        return JSONResponse(400, {"error": "same_language", ...})
    data = await audio.read()
    if len(data) < 1500:
        return _soft("no_speech", "Recording was empty or too short.")
    try:    source_text = transcribe(data, audio.filename or "clip.webm", source_lang)
    except NoSpeechError:  return _soft("no_speech", ...)
    except PipelineError as e:  return _soft("stt_failed", str(e))
    try:    translated_text = translate(source_text, source_lang, target_lang)
    except PipelineError as e:  return _soft("translate_failed", str(e))
    try:    audio_base64 = synthesize(translated_text, target_lang)
    except PipelineError as e:  return _soft("tts_failed", str(e))
    return {"source_text": source_text, "translated_text": translated_text,
            "audio_base64": audio_base64}
```

Notes:
- `response_model=None` on the decorator — FastAPI can't build a response model from the
  `JSONResponse | dict` union and errors at import without it.
- `StaticFiles(directory="static", html=True)` mounted at `/` **after** the `/api` routes.
- CORS not needed (same origin). If serving the HTML from another port in dev, add
  `CORSMiddleware(allow_origins=["*"])` for v1 only.

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
`--host 0.0.0.0` for LAN access. Mobile browsers block `getUserMedia` on non-HTTPS
origins except `localhost` — on-phone testing needs HTTPS (deploy or tunnel).

## Testing without a live key

```python
# STUB_MODE=1
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
c.get("/api/languages")           # 11 codes
c.post("/api/translate-turn", data={"source_lang": "ta-IN", "target_lang": "hi-IN"},
       files={"audio": ("t.webm", b"x" * 4000, "audio/webm")})   # 200 stub
```

## Explicitly NOT in the backend for v1

- No database. Conversation history lives in browser memory; language choice in `localStorage`.
- No `direction` flag — replaced by `source_lang` + `target_lang`.
- No auto-detect, no streaming/websockets, no accounts, no rate limiting of our own.
- No languages beyond the 11 (the non-TTS ones can't produce spoken output).
