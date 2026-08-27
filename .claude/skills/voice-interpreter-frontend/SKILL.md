---
name: voice-interpreter-frontend
description: The single-page frontend for Bhasha Bridge — two big buttons, MediaRecorder mic capture, upload to /api/translate-turn, autoplay of returned base64 audio, and a scrollable turn log. Use when building or debugging static/index.html, mic permissions, mobile browser audio quirks, or the conversation-log UI.
metadata:
  type: project
---

# Bhasha Bridge — Frontend

**Why:** It has to work on a real phone at a doorstep, one-handed, first try. Plain HTML/JS, no build step.
**How to apply:** One `static/index.html` file. Vanilla JS unless you're genuinely faster in React. Talk to the backend contract in [[voice-interpreter-backend]].

## Layout (top to bottom)

1. **Title + one-line story:** "Bhasha Bridge — live Tamil ↔ Hindi voice interpreter. Built after my neighbour couldn't understand his delivery guy."
2. **Turn log** — scrollable, newest at bottom. Each entry: a language tag, the source text, the translated text. Auto-scroll to bottom on new turn.
3. **Two big buttons**, thumb-reachable, side by side or stacked:
   - `🎤 தமிழ் பேசு` (Tamil) → sends `direction: "ta_to_hi"`
   - `🎤 हिंदी बोलें` (Hindi) → sends `direction: "hi_to_ta"`
4. **Status line** under the buttons: idle / "Recording… release to translate" / "Translating…" / error text.

## Recording model

Pick **tap-to-start / tap-to-stop** (more reliable on mobile than press-and-hold, which fights with long-press context menus and scroll).

- While recording: the active button turns red / pulses, the other is disabled.
- On stop: immediately show "Translating…", disable both buttons, POST the blob.
- On response: re-enable buttons, append to log, autoplay audio.

## MediaRecorder capture

```js
let mediaRecorder, chunks = [];

async function startRecording(direction) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  chunks = [];
  const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
    ? 'audio/webm;codecs=opus'
    : (MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4' : '');   // Safari/iOS -> mp4
  mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : {});
  mediaRecorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
  mediaRecorder.onstop = () => {
    stream.getTracks().forEach(t => t.stop());          // release the mic light
    const blob = new Blob(chunks, { type: mediaRecorder.mimeType || 'audio/webm' });
    sendTurn(blob, direction);
  };
  mediaRecorder.start();
}

function stopRecording() {
  if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop();
}
```

## Upload

```js
async function sendTurn(blob, direction) {
  setStatus('Translating…'); setBusy(true);
  const fd = new FormData();
  const ext = (blob.type.includes('mp4') ? 'm4a' : 'webm');
  fd.append('audio', blob, `turn.${ext}`);
  fd.append('direction', direction);
  try {
    const res = await fetch('/api/translate-turn', { method: 'POST', body: fd });
    if (res.status === 422) {
      const j = await res.json().catch(() => ({}));
      return fail(j.error === 'no_speech'
        ? "Didn't catch that — tap and speak a short phrase."
        : "Translation failed. Tap to try again.");
    }
    if (!res.ok) return fail('Network problem. Tap to try again.');
    const { source_text, translated_text, audio_base64 } = await res.json();
    appendTurn(direction, source_text, translated_text);
    playAudio(audio_base64);
    setStatus('Ready');
  } catch {
    fail('No connection. Tap to try again.');
  } finally {
    setBusy(false);
  }
}
```

## Playback

```js
const player = new Audio();
function playAudio(b64) {
  player.src = `data:audio/mp3;base64,${b64}`;
  player.play().catch(() => {/* autoplay blocked — show a ▶ replay button on the turn */});
}
```

- **iOS autoplay:** audio only plays if triggered within a user-gesture chain. Our flow starts from a button tap, but the `await fetch` breaks the gesture context on iOS Safari. Mitigation: on the first button tap, also do `player.play()` on a 0-length/again silent buffer to "unlock" the element, then real playback later works. If it still blocks, render a ▶ button on each turn.
- Give every turn in the log its own ▶ replay button anyway — useful when the listener misses it.

## Failure cases to handle (don't let them freeze the UI)

| case | handling |
|------|----------|
| mic permission denied | catch `getUserMedia` rejection → status: "Allow microphone access to use this, then reload." |
| no `MediaRecorder` / old browser | feature-check on load, show a plain message |
| empty / silent recording | backend returns 422 `no_speech` → "Didn't catch that…" |
| network / server error | "Tap to try again." — buttons stay usable |
| very long press / accidental double tap | guard with a `busy` flag; ignore taps while recording or translating |

## Mobile / UX notes

- Buttons ≥ 64px tall, full-width or half-width, big font, high contrast.
- `<meta name="viewport" content="width=device-width, initial-scale=1">`.
- Keep the page dependency-free — no CDN scripts (works offline-ish, loads instantly on bad connections).
- Latency is 3 chained API calls → 3–6 s. The "Translating…" state must be obvious (spinner or animated dots), never a blank frozen screen.
- Tell the user in the UI copy: "Speak one short sentence at a time."
- Conversation log is **in-memory only** — a refresh clears it. That's fine for v1; don't add storage.

## React (only if faster for you)

Same structure: `useState` for `turns[]`, `status`, `busy`; a `useRef` for the `MediaRecorder` and the `Audio` element. No router, no state library. Still one page, still no persistence.
