# Bhasha Bridge — Project Understanding

## The story (this leads everything, including the social post)

A neighbour couldn't communicate with his Zomato-style delivery guy — one speaks
Tamil, the other Hindi. There's a real moment of confusion at a doorstep that a
phone could solve in ten seconds. **Bhasha Bridge** is a turn-based voice
interpreter for exactly that moment: pick two languages, speak into your phone,
hear it back in the other language.

Tamil ↔ Hindi is just the default. The picker covers **11 Indian languages**.

## What "done" looks like by tomorrow

A single web page, usable on a phone browser:

- Two dropdowns — "Person A speaks" / "Person B speaks" — and a swap button.
- Two big talk buttons, one per person. Person A taps theirs, talks, taps again →
  **A's speech, translated to B's language, shown as text and played as audio**.
  Person B's button does the reverse.
- A scrollable log so it reads like a conversation.

That loop, repeatable, on a real phone, with any of the 11 languages, is the
whole deliverable.

## Why 11 languages, not "all 22"

Sarvam's Speech-to-Text and Translate each cover ~22 languages, but **Text-to-Speech
covers only 11**. A voice interpreter has to speak the output, so the usable set is
the intersection — the 11 languages with STT **and** Translate **and** TTS:

> Hindi, Bengali, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Punjabi,
> Odia, English (all `-IN`).

Both dropdowns list exactly these 11, so every pair works both ways with text and
voice. No "this language can be spoken to but not heard back" dead ends.

## The pipeline (three chained Sarvam calls)

```
audio → Sarvam STT (language_code = source) → transcript
      → Sarvam Translate (source → target)  → target-language text
      → Sarvam TTS (language_code = target) → target-language audio (base64)
```

The two buttons decide which language is `source` and which is `target` for the
turn. See [ARCHITECTURE.md](ARCHITECTURE.md).

## The one risky assumption

Sarvam Translate must do **direct** translation between the chosen pair (e.g.
Tamil→Hindi, Bengali→Tamil) without silently routing through English in a way that
mangles meaning. Verified first, before app polish — Hour 0–0.5 in
[BUILD_PHASES.md](BUILD_PHASES.md). Per Sarvam docs all 11 are first-class codes
for `mayura:v1`, so direct translation is expected; the smoke test confirms quality
on a couple of non-English pairs.

## Explicitly cut from v1

| Cut | Why |
|-----|-----|
| The ~11 languages that have STT+Translate but **no TTS** | Can't speak the output — not a voice interpreter for them |
| Auto language detection | The dropdowns + button choice say everything |
| Continuous / streaming conversation mode | Strict turn-based |
| User accounts, saved history, database (MongoDB) | No user data worth persisting; history lives in browser memory, language choice in `localStorage` |
| Dialect-level granularity | Language codes are enough |
| Fancy UI / design system | Must look *intentional*, not fancy |
| Docker / K8s / custom infra | Free-tier host or local + screen recording |

## Tech stack

- **Backend:** FastAPI. `POST /api/translate-turn` (the pipeline) + `GET /api/languages`
  (dropdown source of truth) + `GET /health`. Serves the static frontend too.
- **AI:** `sarvamai` Python SDK (v0.1.31) — STT, Translate, TTS. Key in `SARVAM_API_KEY`.
  `STUB_MODE=1` short-circuits all Sarvam calls for offline frontend testing.
- **Frontend:** one `static/index.html`, vanilla JS, no build step. `MediaRecorder` for
  mic, `Audio()` for playback. Dropdowns built from `/api/languages`, selection
  persisted in `localStorage`.
- **DB:** none.
- **Deploy:** local + screen recording is the safe demo path; optionally a free-tier
  host (Render / Railway / Fly.io) serving the static frontend from the same app.

## Skills in this repo

- `.claude/skills/sarvam-api` — Sarvam STT/Translate/TTS reference: endpoints, models,
  the 11-language set, SDK call signatures (verified), failure modes, smoke test.
- `.claude/skills/voice-interpreter-backend` — the two endpoints, project layout, config,
  build order, validation rules.
- `.claude/skills/voice-interpreter-frontend` — the single-page UI, dropdowns + swap,
  MediaRecorder capture, base64 playback, mobile quirks.

## Definition of success for the *share*, not just the code

A ~15–20 second video: pick a pair, button tap → voice in → translated voice out,
repeated once. The story in the caption. Honest scope stated ("11 Indian languages,
built in a day"). That post is the actual deliverable; pretty code is secondary.
The picker also invites "add my language" comments — the organic growth loop.
