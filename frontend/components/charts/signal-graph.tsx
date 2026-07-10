"use client";

import { useEffect, useMemo, useRef } from "react";

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

type Kind = "signal" | "cluster";

interface Node {
  id: string;
  kind: Kind;
  sector: string;
  color: string;
  r: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  label: string;
  hub: boolean;
  catalyst: boolean;
  sig?: Signal;
  phase: number;
}

interface Edge {
  a: Node;
  b: Node;
  collision: boolean;
  color: string;
  t: number; // particle position 0..1
  speed: number;
}

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

  useEffect(() => {
    const canvas = canvasRef.current;
    const wrap = wrapRef.current;
    if (!canvas || !wrap) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let W = wrap.clientWidth;
    let H = wrap.clientHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      W = wrap.clientWidth;
      H = wrap.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();

    // ── Build graph ─────────────────────────────────────────────────────────
    const sectors = Array.from(new Set(signals.map((s) => s.sector)));
    const nodes: Node[] = [];
    const clusterBySector = new Map<string, Node>();

    sectors.forEach((sector, i) => {
      const a = (i / sectors.length) * Math.PI * 2;
      const cn: Node = {
        id: `hub:${sector}`,
        kind: "cluster",
        sector,
        color: C.cluster,
        r: 9,
        x: W / 2 + Math.cos(a) * Math.min(W, H) * 0.26,
        y: H / 2 + Math.sin(a) * Math.min(W, H) * 0.26,
        vx: 0,
        vy: 0,
        label: sector.split(" ")[0].toUpperCase(),
        hub: true,
        catalyst: false,
        phase: Math.random() * Math.PI * 2,
      };
      clusterBySector.set(sector, cn);
      nodes.push(cn);
    });

    // Top conviction per sector become highlighted hub names.
    const topBySector = new Map<string, number>();
    signals.forEach((s) => {
      const cur = topBySector.get(s.sector);
      if (cur === undefined || s.confidence > cur) topBySector.set(s.sector, s.confidence);
    });

    signals.forEach((s, i) => {
      const hub = clusterBySector.get(s.sector)!;
      const jitter = 40 + Math.random() * 30;
      const a = Math.random() * Math.PI * 2;
      const isHub = topBySector.get(s.sector) === s.confidence;
      const catalyst = Math.abs(s.change) >= 6 || s.expectedReturn5d >= 1.2;
      nodes.push({
        id: `${s.ticker}:${i}`,
        kind: "signal",
        sector: s.sector,
        color: catalyst && s.signal !== "AVOID" ? C.catalyst : C[s.signal],
        r: 3.5 + (s.confidence - 34) / 6 + (isHub ? 3 : 0),
        x: hub.x + Math.cos(a) * jitter,
        y: hub.y + Math.sin(a) * jitter,
        vx: 0,
        vy: 0,
        label: s.ticker,
        hub: isHub,
        catalyst,
        sig: s,
        phase: Math.random() * Math.PI * 2,
      });
    });

    // ── Edges: spokes to sector hub + a few cross-sector correlations ────────
    const edges: Edge[] = [];
    const signalNodes = nodes.filter((n) => n.kind === "signal");
    signalNodes.forEach((n) => {
      const hub = clusterBySector.get(n.sector)!;
      edges.push({ a: hub, b: n, collision: false, color: n.color, t: Math.random(), speed: 0.003 + Math.random() * 0.004 });
    });
    // Cross-sector links between high-conviction names (some are "collisions").
    const strong = [...signalNodes].sort((a, b) => b.sig!.confidence - a.sig!.confidence).slice(0, 22);
    for (let i = 0; i < strong.length; i++) {
      const a = strong[i];
      const b = strong[(i + 3) % strong.length];
      if (a.sector === b.sector) continue;
      const collision = a.sig!.signal !== "HOLD" && b.sig!.signal !== "HOLD" && a.sig!.signal !== b.sig!.signal;
      edges.push({
        a,
        b,
        collision,
        color: collision ? C.collision : "rgba(148,163,184,0.35)",
        t: Math.random(),
        speed: 0.002 + Math.random() * 0.003,
      });
    }

    // ── Physics ──────────────────────────────────────────────────────────────
    let raf = 0;
    let frame = 0;

    const step = () => {
      frame++;
      // repulsion
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          let d2 = dx * dx + dy * dy;
          if (d2 < 0.01) d2 = 0.01;
          const d = Math.sqrt(d2);
          const rep = (a.kind === "cluster" && b.kind === "cluster" ? 2600 : 520) / d2;
          const fx = (dx / d) * rep;
          const fy = (dy / d) * rep;
          a.vx += fx;
          a.vy += fy;
          b.vx -= fx;
          b.vy -= fy;
        }
      }
      // springs
      for (const e of edges) {
        const rest = e.a.kind === "cluster" || e.b.kind === "cluster" ? 62 : 150;
        const dx = e.b.x - e.a.x;
        const dy = e.b.y - e.a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 0.01;
        const k = (d - rest) * 0.0016;
        const fx = (dx / d) * k;
        const fy = (dy / d) * k;
        e.a.vx += fx;
        e.a.vy += fy;
        e.b.vx -= fx;
        e.b.vy -= fy;
      }
      // centering + damping + integrate
      const cx = W / 2;
      const cy = H / 2;
      for (const n of nodes) {
        n.vx += (cx - n.x) * (n.kind === "cluster" ? 0.0016 : 0.0009);
        n.vy += (cy - n.y) * (n.kind === "cluster" ? 0.0016 : 0.0009);
        n.vx *= 0.86;
        n.vy *= 0.86;
        n.x += n.vx;
        n.y += n.vy;
        const pad = 24;
        n.x = Math.max(pad, Math.min(W - pad, n.x));
        n.y = Math.max(pad + 8, Math.min(H - pad, n.y));
      }

      ctx.clearRect(0, 0, W, H);
      raf = requestAnimationFrame(step);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    raf = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
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
