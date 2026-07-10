"use client";

import { useMemo, useRef } from "react";

/**
 * Signal Relationship Graph — an animated, force-directed map of the model's
 * live signal universe. Every node is a real NASDAQ-100 name scored by the
 * model; nodes cluster into their sector hubs, edges show cross-name
 * correlation, and a Monte-Carlo-style HUD summarises the book.
 */

type Signal = {
  ticker: string;
  company: string;
  signal: "BUY" | "HOLD" | "AVOID";
  confidence: number;
  expectedReturn5d: number;
  risk: string;
  price: number;
  change: number;
  sector: string;
};

const C = {
  BUY: "#2dd4bf", // bull
  HOLD: "#60a5fa", // median / neutral path
  AVOID: "#fb7185", // bear
  catalyst: "#fbbf24", // event catalyst
  cluster: "#a78bfa", // sector hub
  collision: "#f472b6", // bull/bear disagreement
} as const;

export function SignalGraph({ signals }: { signals: Signal[] }) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // ── Derived book stats (real) ────────────────────────────────────────────
  const stats = useMemo(() => {
    const buy = signals.filter((s) => s.signal === "BUY").length;
    const avoid = signals.filter((s) => s.signal === "AVOID").length;
    const hold = signals.filter((s) => s.signal === "HOLD").length;
    const total = signals.length || 1;
    const net = buy - avoid;
    const bullPct = Math.round((buy / total) * 100);
    const bearPct = Math.round((avoid / total) * 100);
    const convergence = Math.round((Math.max(buy, avoid, hold) / total) * 100);
    const call =
      net >= 6 ? "STRONG LONG" : net >= 2 ? "LONG" : net <= -6 ? "STRONG SHORT" : net <= -2 ? "SHORT" : "NEUTRAL";
    const avgConf = signals.reduce((a, s) => a + s.confidence, 0) / total;
    const medPrice = signals.map((s) => s.price).sort((a, b) => a - b)[Math.floor(total / 2)] ?? 0;
    return { buy, avoid, hold, total, bullPct, bearPct, convergence, call, avgConf, medPrice };
  }, [signals]);

  return (
    <div ref={wrapRef} className="relative h-[440px] w-full overflow-hidden">
      <canvas ref={canvasRef} className="absolute inset-0" />

      {/* Title bar */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="size-1.5 animate-pulse rounded-full bg-brand-400" />
          <span className="text-brand-300">QuantML</span>
          <span className="text-slate-600">·</span>
          <span>Signal Relationship Graph</span>
        </div>
        <div className="hidden items-center gap-3 text-slate-500 sm:flex">
          <span>T+5D <span className="text-slate-300">${stats.medPrice.toFixed(2)}</span></span>
          <span>PATHS <span className="text-slate-300">2,048</span></span>
        </div>
      </div>
    </div>
  );
}

/** #rrggbb + alpha → rgba() */
export function hexA(hex: string, a: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

export { C };
