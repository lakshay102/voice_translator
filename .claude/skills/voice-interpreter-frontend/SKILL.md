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

1. **Title + one-line description** — what the product does, in a single sentence.
2. **Two `<select>` dropdowns** — "Person A speaks" / "Person B speaks" — with a **⇄ swap**
   button between them. Populated from `GET /api/languages` on load. Options show
   `native — English` (e.g. `தமிழ் — Tamil`).
3. **Turn log** — scrollable, newest at bottom, auto-scroll. Each entry: a
   `<srcNative> → <tgtNative>` tag, the source text, the translated text, a ▶ replay button.
4. **Two big talk buttons** (one accent colour per person). Labels are **dynamic**:
   `🎤 Speak <native>` with a `<A → B>` sub-label. ≥74px tall, high contrast. **Hold to talk.**
5. **Status line**: `Ready — hold a button to reply` / `Recording… release to translate` /
   `Translating…` / error.

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

## Recording model — hold-to-talk (walkie-talkie)

**Hold a button to record, release (anywhere) to send.** One gesture, no second tap,
natural when passing the phone. Implemented with Pointer Events.

- `pointerdown` on a button → `beginHold(side)`: arm UI, then `getMicStream()`.
- `pointerup` / `pointercancel` (on the button, captured via `setPointerCapture`) → `endHold()`:
  `mediaRecorder.stop()` → `onRecStop` builds the blob and POSTs it.
- Also a `window` `pointerup` + `blur` safety net so a release off the button still ends the turn.
- **Guards:** `MIN_HOLD_MS = 350` and `blob.size < 1200` → treat as an accidental tap,
  discard, show "Hold a little longer and speak". `busy` blocks a new hold while translating.
  If the button is released *before* `getUserMedia` resolves (first-run permission prompt),
  the pending `beginHold` bails on `holdSide !== side`.
- **State:** `holdSide` (button held now), `activeSide` (recording in progress),
  `sendSide` (turn in flight), `busy` (translating). `resetIdle()` clears all of them and
  re-enables both buttons + both selects + swap — call it on **every** completion path
  (success *and* failure) so a second turn always works.
- CSS on `.talk`: `touch-action: none; -webkit-touch-callout: none; user-select: none;` and
  `contextmenu` is `preventDefault`-ed, so a long hold doesn't scroll, zoom, select text, or
  pop the iOS callout.

### Mic stream is acquired once and kept

`getMicStream()` caches the `MediaStream` (`micStream`); it is **not** stopped between turns,
so every turn after the first re-arms instantly (no re-acquire latency, no permission
re-flash). Tracks are stopped only on `pagehide`. A fresh `MediaRecorder` is built from the
same stream each turn. The mic-in-use indicator staying on is expected for a dedicated
interpreter page.

```js
async function getMicStream() {
  if (micStream && micStream.active) return micStream;
  micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  return micStream;
}
function pickMime() {
  if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) return "audio/webm;codecs=opus";
  if (MediaRecorder.isTypeSupported("audio/webm")) return "audio/webm";
  if (MediaRecorder.isTypeSupported("audio/mp4")) return "audio/mp4";   // iOS/Safari
  return "";
}
```

> Note: an earlier tap-to-start/tap-to-stop version had a bug — `activeSide` was never
> cleared after a completed turn, so the *other* person's button was permanently blocked
> (`if (activeSide || busy) return;`). Hold-to-talk + `resetIdle()` on every path fixes it.
> If you refactor, keep the "reset all turn state on completion" invariant.

## Upload

```js
const fd = new FormData();
fd.append("audio", blob, `turn.${blob.type.includes("mp4") ? "m4a" : "webm"}`);
fd.append("source_lang", side === "a" ? selA.value : selB.value);
fd.append("target_lang", side === "a" ? selB.value : selA.value);
const res = await fetch("/api/translate-turn", { method: "POST", body: fd });
// 422 -> {error}: "no_speech" => "Didn't catch that — hold and speak…"; else => "Translation failed. Hold to try again."
// !ok -> "Server problem. Hold to try again."
// 200 -> {source_text, translated_text, audio_base64}
```

## Playback

```js
const player = new Audio();
player.src = "data:audio/mp3;base64," + audio_base64;
player.play().catch(() => setStatus("Tap ▶ replay to hear it"));
```

- **iOS autoplay:** priming needed. `beginHold` calls `unlockAudio()` on the first
  `pointerdown` — set `player.src` to a tiny silent data URI, `play()` then `pause()`
  inside the gesture. After that, post-`fetch` playback works. Every log turn also has a
  ▶ replay button as the fallback.

## Failure cases (never freeze the UI)

| case | handling |
|------|----------|
| mic permission denied | `getUserMedia` rejects → "Allow microphone access, then reload the page." |
| no `MediaRecorder` / old browser | feature-check on load → disable buttons, plain message |
| `/api/languages` fails | "Couldn't load languages. Reload the page." |
| empty / silent recording | backend 422 `no_speech` → "Didn't catch that — hold and speak a short phrase." |
| accidental quick tap (`< 350 ms` / tiny blob) | discarded in `onRecStop`, "Hold a little longer and speak" |
| release lands off the button | `window` `pointerup` / `blur` safety net still ends the turn |
| network / server error | "Hold to try again." — buttons stay usable |
| hold other button mid-turn | ignored via `busy` / `holdSide` / `activeSide` |

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
