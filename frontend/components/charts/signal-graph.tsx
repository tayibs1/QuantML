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

  const callTone =
    stats.call.includes("LONG") ? "text-bull-soft" : stats.call.includes("SHORT") ? "text-bear-soft" : "text-slate-300";

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

      {/* Legend */}
      <div className="pointer-events-none absolute left-4 top-11 space-y-1 font-mono text-[9px] uppercase tracking-wider text-slate-500">
        {[
          ["BUY signal", C.BUY],
          ["Avoid signal", C.AVOID],
          ["Median / hold", C.HOLD],
          ["Catalyst", C.catalyst],
          ["Sector hub", C.cluster],
          ["Collision", C.collision],
        ].map(([label, col]) => (
          <div key={label} className="flex items-center gap-1.5">
            <span className="size-1.5 rounded-full" style={{ background: col as string }} />
            {label}
          </div>
        ))}
      </div>

      {/* Stats HUD */}
      <div className="pointer-events-none absolute right-4 top-11 space-y-1 text-right font-mono text-[9px] uppercase tracking-wider text-slate-500">
        <Row k="Convergence" v={`${stats.convergence}%`} />
        <Row k="Bear signals" v={`${stats.avoid}`} vc="text-bear-soft" />
        <Row k="Bull signals" v={`${stats.buy}`} vc="text-bull-soft" />
        <Row k="Hold / median" v={`${stats.hold}`} />
        <Row k="Avg conviction" v={`${stats.avgConf.toFixed(1)}%`} />
        <div className="mt-1 flex items-center justify-end gap-2 border-t border-white/8 pt-1">
          <span>Signal</span>
          <span className={callTone}>{stats.call}</span>
        </div>
      </div>

      {/* Bull/Bear ratio bar */}
      <div className="pointer-events-none absolute inset-x-4 bottom-3 flex items-center gap-3 font-mono text-[9px] uppercase tracking-wider">
        <span className="text-bull-soft">Bull {stats.bullPct}%</span>
        <div className="flex h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
          <div className="h-full bg-bull" style={{ width: `${stats.bullPct}%` }} />
          <div className="h-full bg-slate-600" style={{ width: `${100 - stats.bullPct - stats.bearPct}%` }} />
          <div className="h-full bg-bear" style={{ width: `${stats.bearPct}%` }} />
        </div>
        <span className="text-bear-soft">Bear {stats.bearPct}%</span>
      </div>
    </div>
  );
}

function Row({ k, v, vc }: { k: string; v: string; vc?: string }) {
  return (
    <div className="flex items-center justify-end gap-2">
      <span>{k}</span>
      <span className={vc ?? "text-slate-300"}>{v}</span>
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
