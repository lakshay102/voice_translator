---
name: voice-interpreter-frontend
description: The single-page frontend for Bhasha Bridge — two language dropdowns (from /api/languages) + swap, two talk buttons, MediaRecorder capture, upload to /api/translate-turn, autoplay of returned base64 audio, and a scrollable turn log. Use when building or debugging static/index.html, the language picker, mic permissions, mobile audio quirks, or the conversation log.
metadata:
  type: project
---

# Bhasha Bridge — Frontend

**Why:** It has to work on a real phone at a doorstep, one-handed, first try. Plain
HTML/JS, no build step, one `static/index.html`.
**How to apply:** Talk to the backend contract in [[voice-interpreter-backend]].

## Layout (top to bottom)

1. **Title + one-line story** — the neighbour / delivery-guy line.
2. **Two `<select>` dropdowns** — "Person A speaks" / "Person B speaks" — with a **⇄ swap**
   button between them. Populated from `GET /api/languages` on load. Options show
   `native — English` (e.g. `தமிழ் — Tamil`).
3. **Turn log** — scrollable, newest at bottom, auto-scroll. Each entry: a
   `<srcNative> → <tgtNative>` tag, the source text, the translated text, a ▶ replay button.
4. **Two big talk buttons** (one accent colour per person). Labels are **dynamic**:
   `🎤 Speak <native>` with a `<A → B>` sub-label. ≥74px tall, high contrast.
5. **Status line**: `Ready` / `Recording… tap again to translate` / `Translating…` / error.

## Language picker

```js
fetch("/api/languages").then(r => r.json()).then(d => populate(d.languages));
// d.languages = [{code, name, native}, …]  — 11 entries
```

- Build identical `<option>` lists for both selects.
- Restore the last pair from `localStorage["bhasha-bridge-langs"] = {a, b}`; default
  `a = ta-IN`, `b = hi-IN` if nothing saved.
- **Never let both selects hold the same code.** On `change`, if they match, move the
  *other* select to the first different code. The swap button just exchanges the two values.
- Persist `{a, b}` on every change.
- `nameOf(code)` → the native name, used in button labels and log tags.

## Direction mapping

Button A pressed → `source_lang = selA.value`, `target_lang = selB.value`.
Button B pressed → the reverse. That's the whole "direction" logic — no flag.

## Recording model

**Tap-to-start / tap-to-stop** (more reliable on mobile than press-and-hold).

- While recording: active button pulses, the other button **and both dropdowns and the
  swap button** are disabled.
- On stop: "Translating…" (animated dots), everything disabled, POST the blob.
- On response: re-enable, append to log, autoplay audio.
- `busy` / `activeSide` flags guard against double-taps and cross-taps.

## MediaRecorder capture

```js
let mime = "";
if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) mime = "audio/webm;codecs=opus";
else if (MediaRecorder.isTypeSupported("audio/webm"))        mime = "audio/webm";
else if (MediaRecorder.isTypeSupported("audio/mp4"))         mime = "audio/mp4";   // iOS/Safari

const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
const rec = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
rec.ondataavailable = e => { if (e.data && e.data.size) chunks.push(e.data); };
rec.onstop = () => {
  stream.getTracks().forEach(t => t.stop());              // release the mic light
  sendTurn(new Blob(chunks, { type: rec.mimeType || mime || "audio/webm" }), side);
};
rec.start();
```

## Upload

```js
const fd = new FormData();
fd.append("audio", blob, `turn.${blob.type.includes("mp4") ? "m4a" : "webm"}`);
fd.append("source_lang", side === "a" ? selA.value : selB.value);
fd.append("target_lang", side === "a" ? selB.value : selA.value);
const res = await fetch("/api/translate-turn", { method: "POST", body: fd });
// 422 -> {error}: "no_speech" => "Didn't catch that…"; else => "Translation failed. Tap to try again."
// !ok -> "Server problem. Tap to try again."
// 200 -> {source_text, translated_text, audio_base64}
```

## Playback

```js
const player = new Audio();
player.src = "data:audio/mp3;base64," + audio_base64;
player.play().catch(() => setStatus("Tap ▶ replay to hear it"));
```

- **iOS autoplay:** priming needed. On the first button tap call `unlockAudio()` — set
  `player.src` to a tiny silent data URI, `play()` then `pause()` inside the gesture.
  After that, post-`fetch` playback works. Every log turn also has a ▶ replay button as
  the fallback.

## Failure cases (never freeze the UI)

| case | handling |
|------|----------|
| mic permission denied | `getUserMedia` rejects → "Allow microphone access, then reload the page." |
| no `MediaRecorder` / old browser | feature-check on load → disable buttons, plain message |
| `/api/languages` fails | "Couldn't load languages. Reload the page." |
| empty / silent recording | backend 422 `no_speech` → "Didn't catch that — tap and speak a short phrase." |
| network / server error | "Tap to try again." — buttons stay usable |
| double-tap / tap other button mid-turn | ignored via `busy` / `activeSide` |

## Mobile / UX notes

- Buttons ≥74px, dropdowns comfortably tappable. `<meta viewport>` with `maximum-scale=1`.
- No CDN scripts — instant load on bad connections.
- Latency 3–6 s (3 chained API calls) → the "Translating…" state must be unmistakable.
- UI copy tells the user: "one short sentence at a time".
- Conversation log is **in-memory only**; a refresh clears it. Language choice survives
  (localStorage). Don't add message storage.

## React (only if faster for you)

Same structure: `useState` for `turns[]`, `status`, `busy`, `langs`, `a`, `b`; `useRef`
for the `MediaRecorder` and the `Audio` element. Fetch `/api/languages` in an effect.
Still one page, still no persistence beyond `localStorage` for the pair.
