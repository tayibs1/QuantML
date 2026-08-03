"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";

// The bits that make swapping from one call to the next feel like the terminal
// retuning rather than a page swap: text that decodes into place, a light bar
// that wipes the chart, and a short settle on everything underneath.

const GLYPHS = "01<>[]{}/\\|=+*#%&$ABCDEF";

/** Runs the characters through noise before locking them in, left to right.
 *  Restarts whenever `trigger` changes. */
export function ScrambleText({
  text,
  trigger,
  className,
  durationMs = 560,
}: {
  text: string;
  trigger: string | number;
  className?: string;
  durationMs?: number;
}) {
  const [shown, setShown] = useState(text);
  const raf = useRef<number | null>(null);

  useEffect(() => {
    const chars = [...text];
    let start: number | null = null;

    const frame = (now: number) => {
      if (start === null) start = now;
      const p = Math.min(1, (now - start) / durationMs);
      // slightly ahead of linear so the tail doesn't feel like it drags
      const locked = p * chars.length * 1.4;
      setShown(
        chars
          .map((ch, i) => {
            if (i < locked || ch === " " || ch === "·") return ch;
            return GLYPHS[(Math.random() * GLYPHS.length) | 0];
          })
          .join("")
      );
      if (p < 1) raf.current = requestAnimationFrame(frame);
      else setShown(text);
    };

    raf.current = requestAnimationFrame(frame);
    // If the tab is hidden the frame loop never runs, so make sure the real text
    // is what's on screen either way.
    const settle = window.setTimeout(() => setShown(text), durationMs + 120);

    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      window.clearTimeout(settle);
      setShown(text);
    };
  }, [text, trigger, durationMs]);

  return <span className={className}>{shown}</span>;
}

/** A bar of light that wipes down the panel once, tinted to the new signal.
 *  Sits on top of the chart and ignores the mouse. */
export function HandoffSweep({ id, accent }: { id: string; accent: string }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl">
      {/* whole-panel flash, gone almost immediately */}
      <motion.div
        key={`${id}-flash`}
        className="absolute inset-0"
        style={{ background: accent }}
        initial={{ opacity: 0.14 }}
        animate={{ opacity: 0 }}
        transition={{ duration: 0.45, ease: "easeOut" }}
      />

      {/* the travelling band */}
      <motion.div
        key={`${id}-band`}
        className="absolute inset-x-0 h-1/2"
        style={{
          background: `linear-gradient(to bottom, transparent, ${accent}14, ${accent}55, ${accent}14, transparent)`,
        }}
        initial={{ y: "-110%" }}
        animate={{ y: "210%" }}
        transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
      />

      {/* bright edge riding the front of the band */}
      <motion.div
        key={`${id}-edge`}
        className="absolute inset-x-0 h-px"
        style={{ background: accent, boxShadow: `0 0 14px 2px ${accent}` }}
        initial={{ y: 0, opacity: 0 }}
        animate={{ y: "100vh", opacity: [0, 0.9, 0.9, 0] }}
        transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  );
}

/** Wraps whatever is being swapped so it settles in rather than popping. */
export function HandoffSettle({
  id,
  delay = 0,
  className,
  children,
}: {
  id: string;
  delay?: number;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <motion.div
      key={id}
      className={className}
      initial={{ opacity: 0, y: 10, filter: "blur(7px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
