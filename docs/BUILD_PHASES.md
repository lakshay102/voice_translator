# Bhasha Bridge — Build Phases

~6.5 hours of build + buffer. Each phase has an exit check — don't move on until it passes.

---

## Hour 0 – 0.5 · Verify the one risky assumption

Before any app code, confirm Sarvam Translate does **direct Tamil↔Hindi**, not a lossy trip through English.

- [ ] `pip install sarvamai`, set `SARVAM_API_KEY` in the shell.
- [ ] Run the smoke test from `.claude/skills/sarvam-api` (§ Quick smoke test): translate a known Tamil sentence → Hindi with `model="mayura:v1"`, `mode="modern-colloquial"`.
- [ ] Repeat Hindi → Tamil.

**Exit check:** both directions return natural, meaning-preserving text. If quality is poor, try `mode="formal"` or `model="sarvam-translate:v1"` and note the choice in `docs/ARCHITECTURE.md`.

---

## Hour 0.5 – 1.5 · Backend skeleton (stubbed)

- [ ] Project layout per `.claude/skills/voice-interpreter-backend` (`app/`, `static/`, `samples/`, `requirements.txt`, `.env.example`).
- [ ] `config.py` — load env, **fail fast** if `SARVAM_API_KEY` missing.
- [ ] `sarvam.py` — `SarvamAI` client singleton + `LANGS` map.
- [ ] `main.py` — `POST /api/translate-turn` accepting `audio` (file) + `direction` (form), plus `load_dotenv()` and static mount.
- [ ] Route returns a **canned** `{source_text, translated_text, audio_base64}` — `audio_base64` = base64 of a tiny beep/silent mp3 checked into `samples/`.
- [ ] `GET /health` → `{"ok": true}`.

**Exit check:** `curl -F audio=@samples/any.webm -F direction=ta_to_hi localhost:8000/api/translate-turn` returns the stub JSON with all three fields.

---

## Hour 1.5 – 3 · Wire the real pipeline

Build `pipeline.py` one function at a time; keep the rest stubbed between steps.

- [ ] `transcribe(audio_bytes, filename, lang_code)` → `client.speech_to_text.transcribe(file=..., model="saaras:v3", language_code=lang_code)` → `.transcript`. Empty/whitespace → raise `SttError("no_speech")`.
- [ ] `translate(text, src, tgt)` → `client.text.translate(...)` → `.translated_text`.
- [ ] `synthesize(text, tgt_lang)` → `client.text_to_speech.convert(..., output_audio_codec="mp3")` → `.audios[0]`.
- [ ] Route chains all three; typed exceptions → 422 `{error, detail}` (`stt_failed` / `translate_failed` / `tts_failed`).
- [ ] `< 1500` byte upload guard → 422 `no_speech`.
- [ ] Record 3–4 voice notes into `samples/` (Tamil + Hindi) and test the full chain against those **before** touching a live mic.

**Exit check:** each sample file → correct `source_text`, sensible `translated_text`, and `audio_base64` that decodes to a playable mp3 (`echo <b64> | base64 -d > out.mp3`).

---

## Hour 3 – 4.5 · Frontend (`static/index.html`)

Per `.claude/skills/voice-interpreter-frontend`.

- [ ] Title + one-line story line.
- [ ] Two big buttons: `🎤 தமிழ் பேசு` (`ta_to_hi`) / `🎤 हिंदी बोलें` (`hi_to_ta`), ≥64px, high contrast.
- [ ] Tap-to-start / tap-to-stop recording with `MediaRecorder`; active button pulses red, other disabled.
- [ ] On stop → POST `FormData(audio, direction)` to `/api/translate-turn`.
- [ ] Loading state: "Translating…" with animated dots/spinner — never a blank frozen screen (budget 3–6 s).
- [ ] On 200: append `{source_text, translated_text}` to an in-memory turn log (scrollable, newest at bottom, auto-scroll), then autoplay `data:audio/mp3;base64,<audio_base64>`.
- [ ] Each log turn gets a ▶ replay button.
- [ ] `<meta viewport>`, no CDN scripts.

**Exit check:** on the laptop at `localhost:8000`, a full spoken turn each direction works end-to-end with autoplay.

---

## Hour 4.5 – 5.5 · Real-world test + rough edges

- [ ] Test on an **actual phone** (see Deployment for the HTTPS requirement).
- [ ] Test with background noise (TV, street) — the real doorstep scenario, not a quiet room.
- [ ] Latency tolerable? If not, tighten UI copy to "one short phrase at a time".
- [ ] Failure cases don't freeze the UI:
  - [ ] mic permission denied → "Allow microphone access, then reload."
  - [ ] empty / silent recording → "Didn't catch that — tap and speak a short phrase."
  - [ ] network / server error → "Tap to try again." (buttons stay usable)
  - [ ] double-tap / tap while busy → ignored via `busy` flag.
- [ ] iOS: confirm autoplay works; if blocked, the ▶ replay button is the fallback.

**Exit check:** hand the phone to someone else; they complete a two-turn conversation without instructions beyond the on-screen copy.

---

## Hour 5.5 – 6.5 · Polish for the demo

- [ ] UI looks *intentional* — consistent spacing, one accent colour, readable fonts. Not fancy, not a raw API tester.
- [ ] On-page description line: "Built this after my neighbour couldn't understand his Zomato delivery guy — Tamil ↔ Hindi live voice interpreter."
- [ ] Record a **15–20 s phone/screen video**: button tap → voice in → translated voice out, repeated once. This is the social post content.
- [ ] Draft the post (see Sharing).

**Exit check:** the video alone communicates what the thing does, with no caption.

---

## Buffer · Deployment

Order of least friction:

1. **Local + screen recording / live on a call** — zero deployment risk. This is the safe default for the demo.
2. **Live & clickable:** one free-tier host for the FastAPI app (Render / Railway / Fly.io), static frontend served by the same app. No Docker/K8s you haven't done before.

### The HTTPS catch for on-phone testing

Mobile browsers block `navigator.mediaDevices.getUserMedia` on non-HTTPS origins — **except** `http://localhost`. So testing on a physically separate phone over `http://<laptop-ip>:8000` will fail at mic access. Options:

- Deploy to a free-tier host (gets you HTTPS for free) and test there.
- Use an HTTPS dev tunnel to the local server.
- Or run Chrome on the phone with the laptop's origin whitelisted via `chrome://flags/#unsafely-treat-insecure-origin-as-secure` (fiddly; last resort).

Set `uvicorn ... --host 0.0.0.0` regardless so the app is reachable on the LAN.

### Deploy checklist

- [ ] `SARVAM_API_KEY` set as a host env var (not committed).
- [ ] `requirements.txt` complete: `fastapi uvicorn[standard] python-multipart python-dotenv sarvamai`.
- [ ] Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- [ ] Static files served by the app (single service, no separate frontend host).
- [ ] Hit the deployed URL from a phone, run one full turn each direction.
- [ ] Rotate / revoke the API key after the demo window if the URL was public.

---

## Buffer · Sharing plan

- **Lead with the story, not the tech:** the neighbour, the delivery guy, the moment of confusion.
- **Video > code screenshots.** ~15–20 s: tap → voice → translated voice, once each way.
- **State the honest scope:** "v1, Tamil↔Hindi only, built in a day." The constraint earns respect and invites "can you add my language?" comments — that's the growth loop.
- Post copy draft:
  > Built this after my neighbour couldn't understand his Zomato delivery guy. Tamil ↔ Hindi live voice interpreter — you talk, it speaks back in the other language. v1, one language pair, built in a day. Video below.

---

## Scope guard (re-read mid-build)

If you're tempted to add any of these, stop: language selector, auto-detect, streaming, a database, accounts, dialect handling, a second endpoint, Docker. All explicitly cut — see [PROJECT_UNDERSTANDING.md](PROJECT_UNDERSTANDING.md#explicitly-cut-from-v1-do-not-scope-creep-mid-build).
