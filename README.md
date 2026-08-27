# Bhasha Bridge

Turn-based voice interpreter for one hardcoded language pair: **Tamil ↔ Hindi**.
Talk into your phone, it speaks back in the other language. Built for the doorstep
moment where a Tamil-speaking resident and a Hindi-speaking delivery person can't
understand each other.

> v1, Tamil ↔ Hindi only, built in a day. No streaming, no accounts, no database.

## How it works

```
audio → Sarvam STT → transcript → Sarvam Translate → target text → Sarvam TTS → audio
```

One endpoint, `POST /api/translate-turn`, with a `direction` flag (`ta_to_hi` /
`hi_to_ta`) that selects the language codes for all three calls.

## Docs

- [docs/PROJECT_UNDERSTANDING.md](docs/PROJECT_UNDERSTANDING.md) — the story, the goal, what's cut
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — the flow, the endpoint contract, language-code map
- [docs/BUILD_PHASES.md](docs/BUILD_PHASES.md) — hour-by-hour build order, deployment, sharing

## Skills (`.claude/skills/`)

- `sarvam-api` — Sarvam STT / Translate / TTS: endpoints, models, language codes, SDK calls, failure modes
- `voice-interpreter-backend` — FastAPI endpoint contract, layout, config, build order
- `voice-interpreter-frontend` — single-page UI, MediaRecorder capture, base64 playback, mobile quirks

## Quick start (once built)

```bash
pip install -r requirements.txt
cp .env.example .env          # add your SARVAM_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000. For on-phone testing you need HTTPS (deploy to a
free-tier host, or use an HTTPS tunnel) — mobile browsers block mic access on
plain-HTTP origins other than `localhost`.

## Stack

FastAPI · `sarvamai` Python SDK · plain HTML/JS single page (`MediaRecorder` +
`<audio>`). No build step, no database.
