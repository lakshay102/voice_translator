---
name: sarvam-api
description: Reference for calling Sarvam AI Speech-to-Text, Translate, and Text-to-Speech — via the sarvamai Python SDK or raw REST. Use whenever writing or debugging code that hits api.sarvam.ai, choosing language codes / model names, or handling STT→Translate→TTS pipelines for the Bhasha Bridge voice interpreter.
metadata:
  type: reference
---

# Sarvam AI API — STT, Translate, TTS

Single source of truth for the three Sarvam calls the voice interpreter chains together.
Verified against docs.sarvam.ai on 2026-08-27. If behaviour differs, trust the live API and update this file.

## Auth

- **REST header:** `api-subscription-key: <KEY>`
- **SDK:** `SarvamAI(api_subscription_key="<KEY>")`
- Key comes from an env var (`SARVAM_API_KEY`). Never hardcode. Never log it.

## SDK install & client

```bash
pip install sarvamai
```

```python
from sarvamai import SarvamAI          # sync
# from sarvamai import AsyncSarvamAI   # async, identical method signatures

client = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
```

---

## 1. Speech-to-Text (STT)

**REST:** `POST https://api.sarvam.ai/speech-to-text` — `multipart/form-data`

**SDK:**
```python
resp = client.speech_to_text.transcribe(
    file=open("clip.wav", "rb"),   # or a file-like object / (name, bytes) tuple
    model="saaras:v3",             # "saaras:v3" (default) or "saaras:v4"
    language_code="ta-IN",         # set from the turn direction; "unknown" = auto-detect
)
transcript = resp.transcript
```

- **Audio formats accepted:** WAV, MP3, AAC, AIFF, OGG, OPUS, FLAC, MP4/M4A, AMR, WMA, **WebM**, PCM.
  Browser `MediaRecorder` output (`audio/webm;codecs=opus`) is accepted directly — no server-side transcode needed for v1.
- **Best results:** 16 kHz sample rate, mono (multi-channel is merged).
- **REST latency budget:** responses return in under ~30 s; keep clips short.
- **`mode`** (optional): `transcribe` (default, keep this), `translate`, `verbatim`, `translit`, `codemix`.
  For our pipeline always use plain `transcribe` and do translation as a separate step — it's controllable and debuggable.
- **Response shape:**
  ```json
  {
    "request_id": "…",
    "transcript": "…",
    "language_code": "ta-IN",
    "language_probability": 0.98
  }
  ```
- **Empty/silent audio** → expect an empty or whitespace `transcript`. Treat that as a user-facing "didn't catch that, try again", not an error.

---

## 2. Translate

**REST:** `POST https://api.sarvam.ai/translate` — JSON body

**SDK:**
```python
resp = client.text.translate(
    input=transcript,
    source_language_code="ta-IN",
    target_language_code="hi-IN",
    model="mayura:v1",             # "mayura:v1" or "sarvam-translate:v1"
    mode="modern-colloquial",     # see below
)
translated = resp.translated_text
```

- **Direct Tamil↔Hindi is supported.** Both `ta-IN` and `hi-IN` are first-class; you do **not** pass through `en-IN`. (Verify once at build time with a known sentence — this is the one risky assumption in the plan.)
- **Char limits:** `mayura:v1` → 1000 chars input; `sarvam-translate:v1` → 2000. A spoken turn is nowhere near this.
- **`mode`** (mayura:v1 only): `formal`, `modern-colloquial`, `classic-colloquial`, `code-mixed`.
  For a doorstep conversation, `modern-colloquial` sounds most natural. `sarvam-translate:v1` only supports `formal`.
- **`output_script`** (mayura:v1): `roman`, `fully-native`, `spoken-form-in-native`. Default native script is what we want for on-screen text and for feeding TTS.
- **`numerals_format`**: `international` (default) or `native`. Keep `international`.
- **Response shape:**
  ```json
  { "request_id": "…", "translated_text": "…", "source_language_code": "ta-IN" }
  ```

---

## 3. Text-to-Speech (TTS)

**REST:** `POST https://api.sarvam.ai/text-to-speech` — JSON body

**SDK:**
```python
resp = client.text_to_speech.convert(
    text=translated,
    language_code="hi-IN",            # SDK param name is `language_code` (REST body uses this too);
                                     # it means the OUTPUT language
    model="bulbul:v2",                # "bulbul:v3" or "bulbul:v2"
    speaker="anushka",                # must be valid for the chosen model (see below)
    speech_sample_rate=22050,
    output_audio_codec="mp3",         # mp3 plays everywhere in an <audio> tag
)
audio_b64 = resp.audios[0]            # base64 string, NOT a data URI

# Verified against sarvamai==0.1.31: transcribe(file=, model=, language_code=),
# text.translate(input=, source_language_code=, target_language_code=, model=, mode=),
# text_to_speech.convert(text=, language_code=, model=, speaker=, speech_sample_rate=, output_audio_codec=)
```

- **Supported `target_language_code`:** `bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, od-IN, pa-IN, ta-IN, te-IN`. Both `hi-IN` and `ta-IN` covered.
- **`text` limit:** 2500 chars (bulbul:v3) / 1500 (bulbul:v2).
- **Speakers must match the model:**
  - `bulbul:v2`: `anushka, manisha, vidya, arya, abhilash, karun, hitesh`
  - `bulbul:v3`: `shubh, aditya, ritu, priya, neha, rahul, pooja, rohan, simran, kavya, …` (large list; check docs)
  - bulbul speakers are **language-agnostic** — a speaker renders whatever `language_code` you pass, so one voice (default `anushka`) covers all 11 languages. A mismatched speaker/**model** pair is a common 400 (e.g. a v3-only speaker with `bulbul:v2`).
- **`speech_sample_rate`:** one of `8000, 16000, 22050, 24000, 32000, 44100, 48000`.
- **`output_audio_codec`:** `mp3, linear16, mulaw, alaw, opus, flac, aac, wav`. Use `mp3`.
- **Response shape:**
  ```json
  { "request_id": "…", "audios": ["<base64>", …] }
  ```
  `audios` is an **array**; take `[0]`. Long text may be split into multiple chunks — for v1, concatenate or just keep turns short enough to be one chunk.

### Turning the base64 into playback

Backend returns the raw base64 string. Frontend builds the data URI:
```js
audioEl.src = `data:audio/mp3;base64,${audio_base64}`;
audioEl.play();
```

---

## Which languages the interpreter offers — TTS is the limiter

The three services don't cover the same set:

| Service | Coverage |
|---|---|
| STT `language_code` | ~22 (`unknown` + 22 codes) |
| Translate `source/target_language_code` | ~22 (+ `auto`) |
| **TTS `language_code`** | **11 only:** `bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, od-IN, pa-IN, ta-IN, te-IN` |

A voice interpreter must speak the output, so the usable set is the **TTS list** — the
11 languages with STT ∩ Translate ∩ TTS. Bhasha Bridge offers exactly these 11 in both
dropdowns, so every pair works both ways with text + audio.

Codes are BCP-47 `xx-IN`. Note **Odia is `od-IN`** (not `or-IN`). No `direction` flag —
the request carries `source_lang` + `target_lang` directly; the frontend enforces
`source_lang != target_lang` and the backend rejects anything outside the 11-set
(`400 bad_language` / `400 same_language`).

Per turn: `transcribe(language_code=source_lang)` → `translate(source_lang → target_lang)`
→ `convert(language_code=target_lang)`. All three take the same code list above; only the
11 TTS ones are ever passed because that's all the UI exposes.

## Failure modes to handle

- **401 / 403** — bad or missing `SARVAM_API_KEY`. Fail loud at startup with a clear message.
- **400 on TTS** — almost always speaker/model mismatch or an unsupported `target_language_code`.
- **Empty transcript** — silent/too-short recording. Return a soft error the UI shows as "try again", HTTP 200 with `{ "error": "no_speech" }` or 422 — pick one and keep it consistent.
- **Timeout / network** — wrap each call, surface a single retry-able error to the client. Don't let one failed call 500 without a JSON body.
- **Rate limits** — free/dev keys are limited; add a small backoff if you batch-test with many clips.

## Quick smoke test (run before building the app)

```python
import os
from sarvamai import SarvamAI

c = SarvamAI(api_subscription_key=os.environ["SARVAM_API_KEY"])
r = c.text.translate(
    input="எனக்கு தண்ணீர் வேண்டும்.",   # "I want water" in Tamil
    source_language_code="ta-IN",
    target_language_code="hi-IN",
    model="mayura:v1",
    mode="modern-colloquial",
)
print(r.translated_text)   # expect natural Hindi ("मुझे पानी चाहिए।"), not garbled English-routed text
```
