# Bhasha Bridge — Build Phases

~6.5 hours of build + buffer. Each phase has an exit check — don't move on until it passes.
Status as of 2026-08-27: backend + frontend wired, passing STUB_MODE tests. Remaining =
live-key verification, real-mic / on-phone testing, polish, deploy, post.

---

## Hour 0 – 0.5 · Verify the one risky assumption

Confirm Sarvam Translate does **direct** translation between non-English pairs, not a lossy
trip through English.

- [ ] `pip install -r requirements.txt`, put a real key in `.env` (`SARVAM_API_KEY=…`, `STUB_MODE=0`).
- [ ] Run the smoke test from `.claude/skills/sarvam-api` (§ Quick smoke test): Tamil → Hindi with `model="mayura:v1"`, `mode="modern-colloquial"`.
- [ ] Repeat with a second non-English pair, e.g. Bengali → Tamil, and Hindi → Tamil.

**Exit check:** all directions return natural, meaning-preserving text. If quality is poor, try `mode="formal"` or `model="sarvam-translate:v1"` and note the choice (set `SARVAM_TRANSLATE_MODE` / `SARVAM_TRANSLATE_MODEL` in `.env`, no code change needed).

---

## Hour 0.5 – 1.5 · Backend skeleton — DONE

- [x] Project layout (`app/`, `static/`, `samples/`, `requirements.txt`, `.env.example`).
- [x] `config.py` — loads env, **fails fast** if `SARVAM_API_KEY` missing (unless `STUB_MODE=1`). `tts_speaker_for(code)` for per-language voice override.
- [x] `sarvam.py` — `SarvamAI` client singleton + `LANGUAGES` (the 11) + `SUPPORTED_CODES` + `language_list()`.
- [x] `main.py` — `POST /api/translate-turn` (`audio` file + `source_lang` + `target_lang`), `GET /api/languages`, `GET /health`, `load_dotenv()`, static mount.
- [x] `STUB_MODE=1` returns canned text + a real ~0.4s silent MP3 (no SDK import, no network).

**Exit check (passing):**
```
curl -F audio=@samples/x.webm -F source_lang=ta-IN -F target_lang=hi-IN localhost:8000/api/translate-turn
```
returns `{source_text, translated_text, audio_base64}`. Validation: `same_language` → 400, unknown code → 400, `<1500` bytes → 422 `no_speech`.

---

## Hour 1.5 – 3 · Real pipeline — DONE (needs live-key verification)

- [x] `transcribe(audio_bytes, filename, lang_code)` → `speech_to_text.transcribe(file=…, model="saaras:v3", language_code=…)` → `.transcript`. Empty → `NoSpeechError`.
- [x] `translate(text, src, tgt)` → `text.translate(input=…, source_language_code=…, target_language_code=…, model="mayura:v1", mode="modern-colloquial")` → `.translated_text`.
- [x] `synthesize(text, tgt_lang)` → `text_to_speech.convert(text=…, language_code=tgt_lang, model="bulbul:v2", speaker=…, speech_sample_rate=22050, output_audio_codec="mp3")` → concat of `.audios`.
- [x] Route chains all three; typed `PipelineError` subclasses → 422 `{error, detail}`.
- [x] `<1500` byte upload guard → 422 `no_speech`.
- [ ] With a live key: record 3–4 voice notes into `samples/` (a couple of language pairs) and test the full chain against files **before** live mic. Decode `audio_base64` and confirm it plays:
      `python -c "import base64,sys;open('out.mp3','wb').write(base64.b64decode(sys.stdin.read()))"`

**Exit check:** each sample → correct `source_text`, sensible `translated_text`, playable mp3.

---

## Hour 3 – 4.5 · Frontend (`static/index.html`) — DONE (needs real-mic test)

- [x] Title + one-line story line.
- [x] Two dropdowns ("Person A speaks" / "Person B speaks") populated from `GET /api/languages`; ⇄ swap button; selection persisted in `localStorage`; the two selects can't both be the same language.
- [x] Two big talk buttons, labels update to the picked languages ("🎤 Speak <native>" + "<A → B>" sub-label), ≥74px, high contrast, one accent colour per person.
- [x] **Hold-to-talk** (walkie-talkie): `pointerdown` records, release (anywhere) sends. Pointer-capture + `window` pointerup/blur safety net; `MIN_HOLD_MS` + tiny-blob guard for accidental taps. Mic stream acquired once and kept for instant re-arm. `resetIdle()` on every completion path so turn 2+ always works.
- [x] On stop → POST `FormData(audio, source_lang, target_lang)`; button A → source=A/target=B, button B → the reverse.
- [x] Animated "Translating…" state (budget 3–6 s).
- [x] On 200: append `{source_text, translated_text}` to in-memory log (scroll, newest at bottom, auto-scroll), autoplay `data:audio/mp3;base64,<audio_base64>`.
- [x] Per-turn ▶ replay button. `<meta viewport>`, no CDN scripts.
- [x] iOS: `audio/mp4` recording fallback + first-tap autoplay unlock; ▶ replay is the fallback if autoplay is blocked.

**Exit check:** on the laptop at `localhost:8000` with a live key, a full spoken turn each direction works end-to-end with autoplay, for at least two different language pairs.

---

## Hour 4.5 – 5.5 · Real-world test + rough edges

- [ ] Test on an **actual phone** (see Deployment for the HTTPS requirement).
- [ ] Test with background noise (TV, street) — the real doorstep scenario, not a quiet room.
- [ ] Try 3–4 language pairs including a Dravidian↔Indo-Aryan one (e.g. Malayalam ↔ Marathi) and one with English.
- [ ] Latency tolerable? If not, lean harder on the "one short phrase" copy.
- [ ] Failure cases don't freeze the UI (all implemented — verify on device):
  - [ ] mic permission denied → "Allow microphone access, then reload the page."
  - [ ] empty / silent recording → "Didn't catch that — tap and speak a short phrase."
  - [ ] network / server / 422 error → "Tap to try again." (buttons stay usable)
  - [ ] quick accidental tap (< 350 ms) → discarded, not sent.
  - [ ] holding the other button mid-turn → ignored.
  - [ ] second and third turns work (regression guard — an earlier tap version blocked turn 2).
- [ ] iOS: confirm autoplay works; if blocked, ▶ replay is the fallback.

**Exit check:** hand the phone to someone else; they pick a pair and complete a two-turn conversation with only the on-screen copy.

---

## Hour 5.5 – 6.5 · Polish for the demo

- [ ] UI looks *intentional* — consistent spacing, readable fonts, the two accent colours doing real work. Not fancy, not a raw API tester.
- [x] On-page description line references the neighbour / delivery-guy story.
- [ ] Record a **15–20 s phone/screen video**: pick a pair → button tap → voice in → translated voice out, repeated once (ideally show switching the language once).
- [ ] Draft the post (see Sharing).

**Exit check:** the video alone communicates what the thing does, with no caption.

---

## Buffer · Deployment

Order of least friction:

1. **Local + screen recording / live on a call** — zero deployment risk. Safe default.
2. **Live & clickable:** one free-tier host for the FastAPI app (Render / Railway / Fly.io), static frontend served by the same app. No Docker/K8s you haven't done before.

### The HTTPS catch for on-phone testing

Mobile browsers block `navigator.mediaDevices.getUserMedia` on non-HTTPS origins — **except** `http://localhost`. Testing on a separate phone over `http://<laptop-ip>:8000` fails at mic access. Options:

- Deploy to a free-tier host (HTTPS for free) and test there.
- Use an HTTPS dev tunnel to the local server.
- Or whitelist the laptop origin on the phone's Chrome via `chrome://flags/#unsafely-treat-insecure-origin-as-secure` (fiddly; last resort).

`.claude/launch.json` already runs `uvicorn ... --host 0.0.0.0` so the app is reachable on the LAN.

### Deploy checklist

- [ ] `SARVAM_API_KEY` set as a host env var (not committed). `STUB_MODE` unset / `0`.
- [ ] `requirements.txt`: `fastapi uvicorn[standard] python-multipart python-dotenv sarvamai`.
- [ ] Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] Static files served by the app (single service, no separate frontend host).
- [ ] Hit the deployed URL from a phone, run one full turn each direction on two pairs.
- [ ] `GET /health` returns `{"ok": true, "stub_mode": false}`.
- [ ] Rotate / revoke the API key after the demo window if the URL was public.

---

## Buffer · Sharing plan

- **Lead with the story, not the tech:** the neighbour, the delivery guy, the moment of confusion.
- **Video > code screenshots.** ~15–20 s: pick a pair, tap → voice → translated voice, once each way.
- **State the honest scope:** "11 Indian languages, turn-based, built in a day." The constraint earns respect and the picker invites "add my language / my dialect" comments — that's the growth loop.
- Post copy draft:
  > Built this after my neighbour couldn't understand his Zomato delivery guy. A live voice interpreter for 11 Indian languages — pick two, talk, and it speaks back in the other. Turn-based, no app install, built in a day. Video below.

---

## Scope guard (re-read mid-build)

Still cut — if tempted, stop: the non-TTS languages, auto-detect, streaming, a database,
accounts, dialect handling, extra endpoints, Docker. See
[PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md#explicitly-cut-from-v1).
