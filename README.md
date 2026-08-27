# Bhasha Bridge

Turn-based voice interpreter for **11 Indian languages** — Hindi, Bengali, Tamil,
Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi, Odia, English. Pick two,
speak into your phone, hear it back in the other language. Built for the doorstep
moment where two people who share no language have to sort out a delivery.

> v1 · 11 languages · turn-based · no streaming, no accounts, no database.

## Why 11 and not 22

Sarvam's Speech-to-Text and Translate cover ~22 languages, but Text-to-Speech
covers only 11. A voice interpreter has to *speak* the output, so the usable set
is the intersection. Both dropdowns list exactly those 11 — every pair works both
ways with text and voice.

## How it works

```
audio → Sarvam STT (source lang) → transcript
      → Sarvam Translate (source → target)
      → Sarvam TTS (target lang) → audio (base64)
```

- `POST /api/translate-turn` — multipart `audio` + `source_lang` + `target_lang`
- `GET /api/languages` — the dropdown list (single source of truth)
- The two talk buttons pick which language is source and which is target.

## Docs

- [docs/PROJECT_UNDERSTANDING.md](docs/PROJECT_UNDERSTANDING.md) — the story, the goal, what's cut
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the flow, endpoint contracts, the 11-language set
- [docs/BUILD_PHASES.md](docs/BUILD_PHASES.md) — build order (with progress), deployment, sharing

## Skills (`.claude/skills/`)

- `sarvam-api` — Sarvam STT / Translate / TTS: endpoints, models, the 11-language set, SDK calls, failure modes
- `voice-interpreter-backend` — the two endpoints, layout, config, validation, build order
- `voice-interpreter-frontend` — single-page UI, language picker, MediaRecorder capture, base64 playback, mobile quirks

## Quick start

```bash
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env          # add your SARVAM_API_KEY, set STUB_MODE=0
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. Set `STUB_MODE=1` to run the UI end-to-end with no
Sarvam calls (canned text + a silent audio clip).

For on-phone testing you need HTTPS (deploy to a free-tier host, or use an HTTPS
tunnel) — mobile browsers block mic access on plain-HTTP origins other than
`localhost`.

## Stack

FastAPI · `sarvamai` Python SDK (v0.1.31) · plain HTML/JS single page
(`MediaRecorder` + `<audio>`). No build step, no database.
