# Bhasha Bridge — Architecture

One flow, any of the 11 supported languages as source or target. The two talk
buttons pick the direction; the two dropdowns pick the language pair.

## Why 11 languages, not 22

Sarvam's three services don't cover the same set:

| Service | Language coverage |
|---|---|
| Speech-to-Text | ~22 |
| Translate | ~22 |
| **Text-to-Speech (bulbul)** | **11** — hi, bn, gu, kn, ml, mr, od, pa, ta, te, en (all `-IN`) |

A voice interpreter must *speak* the output, so the usable set is the TTS list.
Both dropdowns are populated from exactly these 11 (`GET /api/languages`), so every
pair works both ways with text **and** audio. No dead ends.

## Request flow

```
┌─────────────────────────── Phone browser ───────────────────────────┐
│  [ Person A speaks ▾ ]   ⇄   [ Person B speaks ▾ ]                    │
│  [ 🎤 Speak <A> ]              [ 🎤 Speak <B> ]                        │
│      │ tap → record (MediaRecorder, audio/webm;codecs=opus)          │
│      │ tap again → stop                                              │
│      ▼                                                               │
│  POST /api/translate-turn   (multipart/form-data)                    │
│     audio=<blob>                                                     │
│     source_lang=<speaker's language>   target_lang=<listener's>      │
│     (button A → source=A,target=B ; button B → source=B,target=A)    │
└──────────────────────────────┬──────────────────────────────────────┘
                               ▼
┌─────────────────────────── FastAPI ─────────────────────────────────┐
│  validate: both in the 11-set, source_lang != target_lang           │
│                                                                     │
│  1. Sarvam STT       transcribe(audio, language_code=source_lang)   │
│                        → source_text                                │
│  2. Sarvam Translate  translate(source_text, source→target)        │
│                        → translated_text                            │
│  3. Sarvam TTS        synthesize(translated_text, language_code=tgt)│
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

## Endpoints

### `GET /api/languages`
Single source of truth for the dropdowns.
```json
{ "languages": [ { "code": "hi-IN", "name": "Hindi", "native": "हिन्दी" }, … ] }
```

### `POST /api/translate-turn`  (frozen contract — frontend builds against this)
```
multipart/form-data
  audio       : file    MediaRecorder blob
  source_lang : string  one of the 11 codes  (speaker's language)
  target_lang : string  one of the 11 codes  (listener's language, != source_lang)

200 application/json
  { "source_text": str, "translated_text": str, "audio_base64": str }   # base64 mp3, no data: prefix

422 application/json   (soft failure — UI shows a retry message, does not crash)
  { "error": "no_speech" | "stt_failed" | "translate_failed" | "tts_failed", "detail": str }

400 application/json   (bad input)
  { "error": "bad_language" | "same_language", "detail": str }
```

Also: `GET /` serves `static/index.html`; `GET /health` → `{"ok": true, "stub_mode": bool}`.

## Supported languages (the whole selectable set)

`hi-IN` Hindi · `bn-IN` Bengali · `ta-IN` Tamil · `te-IN` Telugu · `kn-IN` Kannada ·
`ml-IN` Malayalam · `mr-IN` Marathi · `gu-IN` Gujarati · `pa-IN` Punjabi ·
`od-IN` Odia · `en-IN` English

Defined once in `app/sarvam.py` as `LANGUAGES` (`SUPPORTED_CODES` is the frozenset).
Note Sarvam uses **`od-IN`** for Odia (not `or-IN`).

## Sarvam calls (see `.claude/skills/sarvam-api` for full detail; verified against sarvamai==0.1.31)

| step | SDK call | key args | output field |
|------|----------|----------|--------------|
| STT | `client.speech_to_text.transcribe` | `file`, `model="saaras:v3"`, `language_code=source_lang` | `.transcript` |
| Translate | `client.text.translate` | `input`, `source_language_code`, `target_language_code`, `model="mayura:v1"`, `mode="modern-colloquial"` | `.translated_text` |
| TTS | `client.text_to_speech.convert` | `text`, **`language_code=target_lang`**, `model="bulbul:v2"`, `speaker`, `speech_sample_rate`, `output_audio_codec="mp3"` | `.audios[0]` (base64, array) |

TTS `speaker` is language-agnostic for bulbul — one default (`anushka`) covers all 11;
override per language with `SARVAM_TTS_SPEAKER_<CODE>`.

## Components

```
app/
  main.py       FastAPI app · load_dotenv · the two routes · static mount
  config.py     Settings, fail-fast if SARVAM_API_KEY missing · model/speaker/rate via env · tts_speaker_for()
  sarvam.py     SarvamAI client singleton · LANGUAGES (11) · SUPPORTED_CODES · language_list()
  pipeline.py   transcribe() / translate() / synthesize() — pure, each raises a typed PipelineError
                (SttError/NoSpeechError/TranslateError/TtsError); STUB_MODE short-circuits each
static/
  index.html    entire frontend, no build step — dropdowns from /api/languages, localStorage-persisted
samples/        pre-recorded voice notes for mic-less testing
```

## State & persistence

**None on the server.** No database (MongoDB explicitly cut). Conversation history is a
JavaScript array in the page; a refresh clears it (language selection is remembered in
`localStorage`). Optional `DEBUG=1` writes the last upload to `samples/_last.<ext>` for
troubleshooting only.

## STUB_MODE

`STUB_MODE=1` (env) makes `pipeline.py` return canned text and a real ~0.4s silent MP3
without importing the SDK or hitting the network — lets the frontend and the full
request/response contract be exercised offline. `/health` reports `stub_mode`.

## Latency budget

3 chained network calls ≈ **3–6 s** per turn. The UI shows an unmistakable animated
"Translating…" state. UI copy asks for "one short sentence at a time" — keeps each call
fast and within the STT ~30 s REST window / TTS char limits.

## Security / config

- `SARVAM_API_KEY` from env (`.env` via `python-dotenv` for local). Never hardcoded, never logged.
- No auth on the endpoints for v1 (demo only). If deployed publicly, treat the key as
  spendable and rotate after the demo.
- `getUserMedia` requires HTTPS on mobile (localhost exempt) — see
  [BUILD_PHASES.md](BUILD_PHASES.md) deployment section.

## Deliberately excluded

Auto language detection · streaming / websockets · DB · accounts / sessions · Docker/K8s ·
dialect handling · the ~11 non-TTS languages. See
[PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md#explicitly-cut-from-v1).
