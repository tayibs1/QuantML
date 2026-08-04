"use client";

// Small synth for the replay page. Every sound is generated on the fly with
// oscillators, so there are no audio files to load and nothing to keep in sync.
//
// Two rules worth knowing before changing anything here:
//   - Browsers refuse to play audio until the user has interacted with the page,
//     so the audio context is only created inside the toggle's click handler.
//   - It stays off unless someone turns it on, and that choice is remembered.

const STORE_KEY = "quantml:sfx";

let ctx: AudioContext | null = null;
let master: GainNode | null = null;
let on = false;

/** Has the user switched sound on? Reads the saved choice on first call. */
export function isOn(): boolean {
  if (typeof window === "undefined") return false;
  return on;
}

export function loadPreference(): boolean {
  if (typeof window === "undefined") return false;
  on = window.localStorage.getItem(STORE_KEY) === "on";
  return on;
}

/** Must be called from a real click, or the browser will keep the context muted. */
export function setOn(next: boolean): boolean {
  on = next;
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORE_KEY, next ? "on" : "off");
  }
  if (next) {
    const c = audio();
    // A context created before any interaction starts suspended.
    if (c && c.state === "suspended") void c.resume();
  }
  return on;
}

function audio(): AudioContext | null {
  if (typeof window === "undefined") return null;
  if (!ctx) {
    const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctor) return null;
    ctx = new Ctor();
    master = ctx.createGain();
    master.gain.value = 0.5;
    master.connect(ctx.destination);
  }
  return ctx;
}

/** One shaped note. `slide` bends the pitch across the note's life. */
function note(opts: {
  from: number;
  to?: number;
  dur: number;
  type?: OscillatorType;
  gain?: number;
  delay?: number;
}) {
  const c = audio();
  if (!c || !master || !on) return;
  const t0 = c.currentTime + (opts.delay ?? 0);
  const osc = c.createOscillator();
  const amp = c.createGain();

  osc.type = opts.type ?? "sine";
  osc.frequency.setValueAtTime(opts.from, t0);
  if (opts.to && opts.to !== opts.from) {
    osc.frequency.exponentialRampToValueAtTime(Math.max(1, opts.to), t0 + opts.dur);
  }

  // Quick fade in and out; a hard start or stop clicks.
  const peak = opts.gain ?? 0.06;
  amp.gain.setValueAtTime(0.0001, t0);
  amp.gain.exponentialRampToValueAtTime(peak, t0 + Math.min(0.02, opts.dur * 0.3));
  amp.gain.exponentialRampToValueAtTime(0.0001, t0 + opts.dur);

  osc.connect(amp);
  amp.connect(master);
  osc.start(t0);
  osc.stop(t0 + opts.dur + 0.02);
}

/** Switching to another call: a short sweep under the light bar. */
export function transition() {
  note({ from: 1200, to: 260, dur: 0.34, type: "triangle", gain: 0.05 });
  note({ from: 180, to: 420, dur: 0.3, type: "sine", gain: 0.035, delay: 0.03 });
}

/** One trading day revealed. Fires many times a second, so it stays quiet and
 *  climbs in pitch as the replay runs, which gives the reveal a sense of rising. */
export function tick(progress: number) {
  const p = Math.max(0, Math.min(1, progress));
  note({ from: 520 + p * 460, dur: 0.045, type: "square", gain: 0.014 });
}

/** The result lands: up and bright when the model was right, down when it wasn't. */
export function outcome(correct: boolean) {
  if (correct) {
    note({ from: 523, dur: 0.16, type: "sine", gain: 0.07 });
    note({ from: 784, dur: 0.34, type: "sine", gain: 0.06, delay: 0.1 });
    note({ from: 1046, dur: 0.5, type: "sine", gain: 0.035, delay: 0.2 });
  } else {
    note({ from: 392, dur: 0.2, type: "triangle", gain: 0.06 });
    note({ from: 262, dur: 0.5, type: "triangle", gain: 0.05, delay: 0.12 });
  }
}

/** Play pressed: a small rising blip so starting a run feels deliberate. */
export function arm() {
  note({ from: 340, to: 680, dur: 0.14, type: "triangle", gain: 0.05 });
}
