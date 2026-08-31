# Bhasha Bridge — Project Description

**One line:** A turn-based voice interpreter for 11 Indian languages, built on Sarvam AI's speech and translation APIs.

**Live demo:** <add your deployed URL>
**Source code:** <add your GitHub repo URL>
**Demo video:** <add your video URL>

---

## 1. The problem

India has 22 scheduled languages and no single lingua franca at street level. The
everyday failure case is small but constant: a delivery agent and a customer, an
auto driver and a passenger, a nurse and a patient's family — two people standing
face to face who share no common language and just need to sort out one concrete
thing (an address, a price, a symptom, a time).

Existing tools don't fit that moment. Generic translation apps are built around
typing, are English-centric (they often route Indian language A → English →
Indian language B, losing meaning), and are awkward to pass back and forth in a
live conversation.

## 2. What Bhasha Bridge does

Two people pick their languages once from two dropdowns. Then they take turns:

1. Person A holds a button and speaks a short phrase in their language.
2. On release, the app transcribes it, translates it directly into Person B's
   language, and plays the result out loud in a natural voice.
3. Person B holds the other button and replies. The app translates back.
4. Every turn is written into an on-screen log (original + translation) so
   nothing is lost and either person can re-read or replay it.

It is deliberately **turn-based, not real-time streaming** — that matches how two
strangers actually hand a phone back and forth, and it keeps the build honest and
robust for v1.

### Design decisions

| Decision | Why |
| --- | --- |
| **11 languages, not 22** | Sarvam STT and Translate cover ~22 languages, but TTS (bulbul) covers 11. A voice interpreter must *speak* its output, so the usable set is the intersection: Hindi, Bengali, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi, Odia, English. Every pair works both ways, in text and voice. |
| **Direct A→B translation** | Sarvam Translate does direct Indian-language-to-Indian-language translation (`mayura:v1`, `mode="modern-colloquial"`), so we skip the lossy pivot through English and get colloquial, doorstep-appropriate phrasing. |
| **Hold-to-talk** | An explicit press/release gives clean recording boundaries, no voice-activity detection, no accidental capture, and an obvious mental model when handing the phone over. |
| **No accounts, no database** | The turn log lives in memory in the page. Nothing is stored server-side, nothing is saved after the tab closes. Lower friction, nothing sensitive to leak. |
| **Single-page, no build step** | Plain HTML + JS (`MediaRecorder` + `<audio>`). Works on a phone browser, which is where this is actually used. |

## 3. How it works

```
                 ┌─────────────────────────  browser (static/index.html)  ──────────────────────────┐
                 │  2 language dropdowns (from /api/languages) + swap                                │
                 │  2 hold-to-talk buttons → MediaRecorder captures a short clip                     │
                 │  POST the clip + source_lang + target_lang                                        │
                 │  autoplay returned audio · append original + translation to the turn log          │
                 └───────────────────────────────────────┬─────────────────────────────────────────┘
                                                         │  multipart/form-data
                                                         ▼
   ┌──────────────────────────  FastAPI backend (app/)  ─────────────────────────────┐
   │  POST /api/translate-turn                                                        │
   │    1. Sarvam Speech-to-Text   speech_to_text.transcribe(file, model="saaras:v3",│
   │                               language_code=source_lang)      → transcript       │
   │    2. Sarvam Translate        text.translate(input, source_language_code,        │
   │                               target_language_code, model="mayura:v1",           │
   │                               mode="modern-colloquial")       → translated_text  │
   │    3. Sarvam Text-to-Speech   text_to_speech.convert(text, language_code=target, │
   │                               model="bulbul:v2", speaker=…)   → base64 mp3        │
   │    → 200 { source_text, translated_text, audio_base64 }                          │
   │    → 422 { error: no_speech | stt_failed | translate_failed | tts_failed }       │
   │                                                                                  │
   │  GET /api/languages   → the 11-language list (single source of truth)            │
   │  GET /health                                                                    │
   └──────────────────────────────────────┬─────────────────────────────────────────┘
                                          │
                                          ▼
                              Sarvam AI API (api.sarvam.ai)
                              via the `sarvamai` Python SDK
```

### Sarvam AI services used

| Step | Sarvam service | SDK call | Model | Key inputs → output |
| --- | --- | --- | --- | --- |
| 1 | **Speech-to-Text** | `client.speech_to_text.transcribe()` | `saaras:v3` | audio file, `language_code` → `transcript` |
| 2 | **Text Translation** | `client.text.translate()` | `mayura:v1`, `mode=modern-colloquial` | `input`, `source_language_code`, `target_language_code` → `translated_text` |
| 3 | **Text-to-Speech** | `client.text_to_speech.convert()` | `bulbul:v2`, per-language speaker, 22.05 kHz, mp3 | `text`, `language_code` → base64 mp3 |

All three are chained per conversation turn in `app/pipeline.py`. The client is a
lazily-built `SarvamAI(api_subscription_key=SARVAM_API_KEY)` singleton; the key
comes from an environment variable and is never hardcoded or logged.

## 4. Tech stack

- **Backend:** Python, FastAPI, `sarvamai` SDK (v0.1.31), Uvicorn
- **Frontend:** single static HTML page, vanilla JS, `MediaRecorder` API, `<audio>` playback — no framework, no build
- **Config:** `.env` via `python-dotenv`; every model / voice / sample-rate overridable by env var
- **No database, no auth, no external state**

### Robustness details

- Server validates that both language codes are supported and that source ≠ target.
- Recordings under ~1.5 KB are rejected as "no speech" before any Sarvam call (saves quota on accidental taps).
- Each pipeline step raises a typed error mapped to a soft `422` with a specific
  `error` code, so the frontend can show a useful message instead of a generic failure.
- `STUB_MODE=1` runs the whole UI round-trip (including audio playback) with
  canned text and a silent clip and **no** Sarvam calls / no API key — used for
  offline frontend work and for CI.

## 5. Repository layout

```
sarvam_ai/
├── app/
│   ├── main.py       FastAPI app: /api/translate-turn, /api/languages, /health, static mount
│   ├── pipeline.py   transcribe() / translate() / synthesize() — the 3 Sarvam calls, typed errors, STUB_MODE
│   ├── sarvam.py     SarvamAI client singleton · the 11-language table · language_list()
│   └── config.py     Settings, fail-fast on missing SARVAM_API_KEY, per-language voice overrides
├── static/index.html single-page frontend
├── docs/             project understanding, architecture, build phases
└── requirements.txt
```

## 6. Running it

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env          # add SARVAM_API_KEY, set STUB_MODE=0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`. On-phone testing needs an HTTPS origin (deploy to a
free-tier host or use an HTTPS tunnel) because mobile browsers block microphone
access on non-`localhost` plain-HTTP pages.

## 7. Scope boundaries (v1)

**In:** 11 languages, both directions, voice in / voice out, on-screen turn log, mobile browser support, graceful per-step error messages.

**Deliberately out:** real-time / streaming translation, speaker diarization, more than two participants, transliteration, saved history / accounts / database, offline mode, a native app.

## 8. Possible next steps

- Streaming STT for lower latency on longer turns
- "Detect language" mode so neither person has to pick
- Downloadable transcript of a conversation
- Wider language set if/when Sarvam TTS expands
- PWA install + reconnect handling for flaky mobile networks
