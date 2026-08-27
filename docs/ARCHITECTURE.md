# Bhasha Bridge — Architecture

One flow, both directions. Direction is a flag, not a second code path.

## Request flow

```
┌─────────────────────────── Phone browser ───────────────────────────┐
│  [ 🎤 Tamil ]   [ 🎤 Hindi ]                                         │
│      │ tap → record (MediaRecorder, audio/webm;codecs=opus)         │
│      │ release → stop                                                │
│      ▼                                                               │
│  POST /api/translate-turn   (multipart/form-data)                    │
│     audio=<blob>   direction="ta_to_hi" | "hi_to_ta"                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────── FastAPI ─────────────────────────────────┐
│  direction → LANGS[direction] = {stt, src, tgt}                      │
│                                                                     │
│  1. Sarvam STT       transcribe(audio, language_code=stt)           │
│                        → source_text  (speaker's language)          │
│  2. Sarvam Translate  translate(source_text, src → tgt)             │
│                        → translated_text  (listener's language)     │
│  3. Sarvam TTS        synthesize(translated_text, target=tgt)       │
│                        → audio_base64  (mp3, base64)                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
        200 JSON { source_text, translated_text, audio_base64 }
                               ▼
┌─────────────────────────── Phone browser ───────────────────────────┐
│  append { source_text, translated_text } to in-memory turn log      │
│  audio.src = "data:audio/mp3;base64," + audio_base64 ; audio.play() │
└─────────────────────────────────────────────────────────────────────┘
```

## The endpoint contract (frozen — frontend builds against this before the pipeline is real)

```
POST /api/translate-turn
Content-Type: multipart/form-data
  audio     : file   MediaRecorder blob
  direction : string "ta_to_hi" | "hi_to_ta"

200 application/json
  { "source_text": str, "translated_text": str, "audio_base64": str }   # base64 mp3, no data: prefix

422 application/json   (soft failure — UI shows a retry message, does not crash)
  { "error": "no_speech" | "stt_failed" | "translate_failed" | "tts_failed", "detail": str }

400 — malformed direction
```

Also: `GET /` serves `static/index.html`; optional `GET /health` → `{"ok": true}`.

## Direction → language codes (the entire switch)

```python
LANGS = {
    "ta_to_hi": {"stt": "ta-IN", "src": "ta-IN", "tgt": "hi-IN"},
    "hi_to_ta": {"stt": "hi-IN", "src": "hi-IN", "tgt": "ta-IN"},
}
```

| direction  | STT `language_code` | Translate `source→target` | TTS `target_language_code` |
|------------|---------------------|---------------------------|----------------------------|
| `ta_to_hi` | `ta-IN`             | `ta-IN` → `hi-IN`         | `hi-IN`                    |
| `hi_to_ta` | `hi-IN`             | `hi-IN` → `ta-IN`         | `ta-IN`                    |

## Sarvam calls (see `.claude/skills/sarvam-api` for full detail)

| step | SDK call | key args | output field |
|------|----------|----------|--------------|
| STT | `client.speech_to_text.transcribe` | `file`, `model="saaras:v3"`, `language_code` | `.transcript` |
| Translate | `client.text.translate` | `input`, `source_language_code`, `target_language_code`, `model="mayura:v1"`, `mode="modern-colloquial"` | `.translated_text` |
| TTS | `client.text_to_speech.convert` | `text`, `target_language_code`, `model="bulbul:v2"`, `speaker`, `output_audio_codec="mp3"` | `.audios[0]` (base64) |

## Components

```
app/
  main.py       FastAPI app · load_dotenv · CORS (dev only) · the one route · static mount
  config.py     Settings, fail-fast if SARVAM_API_KEY missing · model/speaker overrides via env
  sarvam.py     SarvamAI client singleton · LANGS map
  pipeline.py   transcribe() / translate() / synthesize() — pure, each raises a typed error
static/
  index.html    entire frontend, no build step
samples/        pre-recorded voice notes for mic-less testing
```

## State & persistence

**None on the server.** No database (MongoDB explicitly cut). Conversation history is a JavaScript array in the page; a refresh clears it. Optional `DEBUG=1` writes the last upload to `samples/_last.webm` for troubleshooting only.

## Latency budget

3 chained network calls ≈ **3–6 s** per turn. The UI must show an unmistakable "Translating…" state. Guidance in the UI copy: "Speak one short sentence at a time" — keeps each call fast and within the STT ~30 s REST window / TTS char limits.

## Security / config

- `SARVAM_API_KEY` from env (`.env` via `python-dotenv` for local). Never hardcoded, never logged.
- No auth on the endpoint for v1 (demo only). If deployed publicly, treat the key as spendable and rotate after the demo.
- `getUserMedia` requires HTTPS on mobile (localhost exempt) — see [BUILD_PHASES.md](BUILD_PHASES.md) deployment section.

## Deliberately excluded

Second endpoint · language selector · auto-detect · streaming / websockets · DB · accounts / sessions · Docker/K8s. See [PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md#explicitly-cut-from-v1-do-not-scope-creep-mid-build).
