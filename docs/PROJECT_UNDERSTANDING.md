# Bhasha Bridge — Project Understanding

## The story (this leads everything, including the social post)

A neighbour couldn't communicate with his Zomato/Zomato-style delivery guy — neighbour speaks Tamil, delivery guy speaks Hindi. There's a real moment of confusion at a doorstep that a phone could solve in ten seconds. **Bhasha Bridge** is a turn-based voice interpreter for exactly that moment: Tamil ↔ Hindi, spoken in, spoken out.

## What "done" looks like by tomorrow

A single web page, usable on a phone browser, with two big buttons:

- Tamil speaker taps their button, talks, releases → **Hindi text + spoken Hindi audio** plays out for the delivery guy.
- Delivery guy taps their button, talks in Hindi, releases → **Tamil text + spoken Tamil audio** plays back.

That loop, repeatable, on a real phone, is the entire deliverable. Everything else is out of scope.

## Why it's scoped this tight

One hardcoded language pair, turn-based, no streaming, no database, no accounts. The constraint is the point — it ships in a day, it demos cleanly, and "v1, Tamil↔Hindi only, built in a day" is a more honest and more shareable story than a half-working 22-language selector.

## The pipeline (three chained Sarvam calls)

```
audio → Sarvam STT → native transcript
      → Sarvam Translate → target-language text
      → Sarvam TTS → target-language audio (base64)
```

Direction (`ta_to_hi` / `hi_to_ta`) is a single flag that picks the language codes for all three calls. See [ARCHITECTURE.md](ARCHITECTURE.md).

## The one risky assumption

Sarvam Translate must do **direct Tamil→Hindi** (and Hindi→Tamil) without silently routing through English in a way that mangles meaning. This is verified first, before any app code — Hour 0–0.5 in [BUILD_PHASES.md](BUILD_PHASES.md). Per Sarvam docs both `ta-IN` and `hi-IN` are first-class language codes for `mayura:v1`, so direct translation is expected; the smoke test confirms quality.

## Explicitly cut from v1 (do not scope-creep mid-build)

| Cut | Why |
|-----|-----|
| Generic 22-language selector | Hardcoded Tamil/Hindi only |
| Auto language detection | The button choice tells you the language |
| Continuous / streaming conversation mode | Strict turn-based |
| User accounts, saved history, database (MongoDB) | No user data worth persisting; history lives in browser memory |
| Dialect-level granularity | `ta-IN` / `hi-IN` language codes are enough |
| Fancy UI / design system | Must look *intentional*, not fancy |
| Docker / K8s / custom infra | Free-tier host or local + screen recording |

## Tech stack

- **Backend:** FastAPI, one `POST /api/translate-turn` route. Serves the static frontend too.
- **AI:** `sarvamai` Python SDK — STT, Translate, TTS. API key in `SARVAM_API_KEY` env var.
- **Frontend:** one `static/index.html`, vanilla JS, `MediaRecorder` for mic, `<audio>` / `Audio()` for playback. No build step. React only if genuinely faster for the builder.
- **DB:** none.
- **Deploy:** local + screen recording is the safe demo path; optionally a free-tier host (Render / Railway / Fly.io) with the static frontend served from the same app.

## Skills in this repo

- `.claude/skills/sarvam-api` — Sarvam STT/Translate/TTS reference: endpoints, models, language codes, SDK calls, failure modes, smoke test.
- `.claude/skills/voice-interpreter-backend` — the FastAPI endpoint contract, project layout, config, build order.
- `.claude/skills/voice-interpreter-frontend` — the single-page UI, MediaRecorder capture, upload, base64 playback, mobile quirks.

## Definition of success for the *share*, not just the code

A ~15–20 second video showing: button tap → voice in → translated voice out, repeated once. The story in the caption. Honest scope stated. That post is the actual deliverable; pretty code is secondary.
