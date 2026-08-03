"use client";

import { useEffect, useMemo, useRef, useState } from "react";

// Force-directed map of the current signal book. Each node is a scored name;
// nodes pull toward their sector hub and edges link correlated names.
// Canvas + requestAnimationFrame, fed by the signals snapshot.

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

// Slows everything that moves, without changing where the layout settles.
// Lower is calmer: nodes glide into place instead of snapping there.
const MOTION = 0.5;

// A force-directed layout goes still once it balances out. This keeps a slow
// wander running underneath so the book always looks live, without pulling the
// arrangement apart.
const WANDER = 0.055;

// How much speed a node keeps between frames. Raising this makes the drift
// springy rather than slow, so it stays where it is and MOTION does the slowing.
const GLIDE = 0.86;

// How far the cursor's influence reaches, and how hard it shoves. The push is
// kept mild on purpose: the springs holding each name to its sector hub should
// win, so the book bulges around the cursor and settles back rather than
// scattering out of reach of a hover.
const CURSOR_REACH = 180;
const CURSOR_PUSH = 0.8;
// Nothing right under the cursor gets pushed, so the name you are pointing at
// stays put and can still be hovered while its neighbours scatter around it.
const CURSOR_HOLD = 26;
// A little sideways drift on top of the push, so they curl around the cursor
// instead of only running from it.
const CURSOR_SWIRL = 0.35;

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

export function SignalGraph({
  signals,
  height = 440,
  compact = false,
}: {
  signals: Signal[];
  /** canvas height in px */
  height?: number;
  /** drop the legend and stats HUD for a slim strip */
  compact?: boolean;
}) {
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [hover, setHover] = useState<{ node: Node; x: number; y: number } | null>(null);
  const [iter, setIter] = useState(49_772);

  // book stats shown in the HUD
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
    let seeded = false;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      const prevW = W;
      const prevH = H;
      W = wrap.clientWidth;
      H = wrap.clientHeight;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      canvas.style.width = `${W}px`;
      canvas.style.height = `${H}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      // Switching to cinematic roughly doubles the panel width. Stretch the
      // layout that's already on screen into the new space, otherwise it stays
      // huddled where it started and slowly creeps outward.
      if (seeded && prevW > 0 && prevH > 0 && (W !== prevW || H !== prevH)) {
        const sx = W / prevW;
        const sy = H / prevH;
        for (const n of nodes) {
          n.x *= sx;
          n.y *= sy;
        }
      }
    };
    resize();

    // ── Build graph ─────────────────────────────────────────────────────────
    const sectors = Array.from(new Set(signals.map((s) => s.sector)));
    const nodes: Node[] = [];
    const clusterBySector = new Map<string, Node>();

    // Sector hubs sit on an ellipse shaped like the panel rather than a circle.
    // On a wide, short panel a circle would bunch every hub into the middle and
    // leave the ends bare.
    const spreadX = W * 0.36;
    const spreadY = H * 0.3;

    sectors.forEach((sector, i) => {
      const a = (i / sectors.length) * Math.PI * 2;
      const cn: Node = {
        id: `hub:${sector}`,
        kind: "cluster",
        sector,
        color: C.cluster,
        r: 9,
        x: W / 2 + Math.cos(a) * spreadX,
        y: H / 2 + Math.sin(a) * spreadY,
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

    // highest-conviction name per sector becomes a hub
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

    // Positions exist from here on, so a resize can carry them across.
    seeded = true;

    // ── Edges: spokes to sector hub + a few cross-sector correlations ────────
    const edges: Edge[] = [];
    const signalNodes = nodes.filter((n) => n.kind === "signal");
    signalNodes.forEach((n) => {
      const hub = clusterBySector.get(n.sector)!;
      edges.push({ a: hub, b: n, collision: false, color: n.color, t: Math.random(), speed: 0.003 + Math.random() * 0.004 });
    });
    // Cross-sector links between high-conviction names (some are "collisions").
    const strong = [...signalNodes].sort((a, b) => (b.sig!.confidence - a.sig!.confidence)).slice(0, 22);
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
    let lastHoverId = "";
    const mouse = { x: -1, y: -1 };

    const onMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      // The rect is in screen pixels and cinematic scales the whole page down,
      // so convert back into the canvas's own coordinates. Without this the
      // cursor's effect lands somewhere off to the side of where it actually is.
      const kx = rect.width ? canvas.offsetWidth / rect.width : 1;
      const ky = rect.height ? canvas.offsetHeight / rect.height : 1;
      mouse.x = (e.clientX - rect.left) * kx;
      mouse.y = (e.clientY - rect.top) * ky;
    };
    const onLeave = () => {
      mouse.x = -1;
      mouse.y = -1;
      setHover(null);
    };
    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mouseleave", onLeave);

    const step = () => {
      frame++;
      // forces
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          let dx = a.x - b.x;
          let dy = a.y - b.y;
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

      // cursor: shove nearby names aside, with a bit of curl
      if (mouse.x > 0) {
        for (const n of nodes) {
          const dx = n.x - mouse.x;
          const dy = n.y - mouse.y;
          const d = Math.hypot(dx, dy) || 0.01;
          if (d >= CURSOR_REACH || d < CURSOR_HOLD) continue;
          // falls off toward the edge of reach so there's no hard boundary
          const falloff = 1 - (d - CURSOR_HOLD) / (CURSOR_REACH - CURSOR_HOLD);
          const push = falloff * falloff * CURSOR_PUSH;
          n.vx += (dx / d) * push;
          n.vy += (dy / d) * push;
          n.vx += (-dy / d) * push * CURSOR_SWIRL;
          n.vy += (dx / d) * push * CURSOR_SWIRL;
        }
      }

      // centering + damping + integrate
      const cx = W / 2;
      const cy = H / 2;
      let hoverNode: Node | null = null;
      // a little wider than the dot, since the cursor nudges names away from it
      let hoverDist = 22;
      // The pull back to the middle is gentler sideways than vertically, in
      // proportion to how wide the panel is, so the book keeps the width it was
      // given instead of collapsing into a blob in the centre.
      const wide = Math.min(3, Math.max(1, W / Math.max(H, 1)));
      const t = frame * 0.007;
      for (const n of nodes) {
        const k = n.kind === "cluster" ? 0.0016 : 0.0009;
        n.vx += (cx - n.x) * (k / wide);
        n.vy += (cy - n.y) * k;

        // Each name drifts on its own timing - the phase it was given at setup
        // keeps them from swaying together. Hubs wander less so the sectors stay
        // where you left them.
        const w = n.kind === "cluster" ? WANDER * 0.4 : WANDER;
        n.vx += Math.cos(t + n.phase) * w;
        n.vy += Math.sin(t * 0.87 + n.phase * 1.3) * w;
        n.vx *= GLIDE;
        n.vy *= GLIDE;
        n.x += n.vx * MOTION;
        n.y += n.vy * MOTION;
        const pad = 24;
        n.x = Math.max(pad, Math.min(W - pad, n.x));
        n.y = Math.max(pad + 8, Math.min(H - pad, n.y));
        if (mouse.x > 0) {
          const md = Math.hypot(mouse.x - n.x, mouse.y - n.y);
          if (n.kind === "signal" && md < hoverDist && md < hoverDist) {
            hoverDist = md;
            hoverNode = n;
          }
        }
      }

      // ── Render ──────────────────────────────────────────────────────────────
      ctx.clearRect(0, 0, W, H);

      // soft pool of light under the cursor, so its reach is visible
      if (mouse.x > 0) {
        const halo = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, CURSOR_REACH);
        halo.addColorStop(0, "rgba(45,212,191,0.10)");
        halo.addColorStop(0.55, "rgba(45,212,191,0.03)");
        halo.addColorStop(1, "rgba(45,212,191,0)");
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(mouse.x, mouse.y, CURSOR_REACH, 0, Math.PI * 2);
        ctx.fill();
      }

      // edges
      for (const e of edges) {
        ctx.beginPath();
        ctx.moveTo(e.a.x, e.a.y);
        ctx.lineTo(e.b.x, e.b.y);
        ctx.strokeStyle = e.collision ? "rgba(244,114,182,0.28)" : "rgba(148,163,184,0.10)";
        ctx.lineWidth = e.collision ? 1.1 : 0.7;
        ctx.stroke();

        // travelling particle
        e.t += e.speed * MOTION;
        if (e.t > 1) e.t -= 1;
        const px = e.a.x + (e.b.x - e.a.x) * e.t;
        const py = e.a.y + (e.b.y - e.a.y) * e.t;
        ctx.beginPath();
        ctx.arc(px, py, e.collision ? 1.7 : 1.2, 0, Math.PI * 2);
        ctx.fillStyle = e.collision ? C.collision : e.color;
        ctx.globalAlpha = 0.9;
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      // nodes
      for (const n of nodes) {
        // Slow breathing on the hubs and catalysts. A deeper swing than the drift
        // gives the eye something to follow while the layout barely moves.
        const pulse = n.hub || n.catalyst ? 0.5 + 0.5 * Math.sin(frame * 0.06 * MOTION + n.phase) : 0;
        const glowR = n.r * (n.kind === "cluster" ? 5 : 4) + pulse * 10;
        const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glowR);
        g.addColorStop(0, hexA(n.color, 0.55));
        g.addColorStop(0.4, hexA(n.color, 0.16));
        g.addColorStop(1, hexA(n.color, 0));
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(n.x, n.y, glowR, 0, Math.PI * 2);
        ctx.fill();

        // core
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();
        if (n.hub || n.kind === "cluster") {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r + 2.5 + pulse * 4, 0, Math.PI * 2);
          ctx.strokeStyle = hexA(n.color, 0.3 + pulse * 0.35);
          ctx.lineWidth = 1;
          ctx.stroke();
        }

        // label for hubs / clusters / hovered
        if (n.kind === "cluster" || n.hub || n === hoverNode) {
          ctx.font = `600 ${n.kind === "cluster" ? 9 : 8.5}px ui-monospace, monospace`;
          ctx.fillStyle = n.kind === "cluster" ? hexA(n.color, 0.85) : "rgba(226,232,240,0.85)";
          ctx.textAlign = "center";
          ctx.fillText(n.label, n.x, n.y - n.r - 5);
        }
      }

      // only touch React state when the hovered node changes
      const hoverId = hoverNode?.id ?? "";
      if (hoverId !== lastHoverId) {
        lastHoverId = hoverId;
        setHover(hoverNode && hoverNode.sig ? { node: hoverNode, x: hoverNode.x, y: hoverNode.y } : null);
      } else if (hoverNode && hoverNode.sig) {
        // follow the node as it drifts
        setHover({ node: hoverNode, x: hoverNode.x, y: hoverNode.y });
      }

      if (frame % 25 === 0) setIter((v) => v + Math.floor(6 + Math.random() * 18));

      raf = requestAnimationFrame(step);
    };

    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    raf = requestAnimationFrame(step);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mouseleave", onLeave);
    };
  }, [signals]);

  const callTone =
    stats.call.includes("LONG") ? "text-bull-soft" : stats.call.includes("SHORT") ? "text-bear-soft" : "text-slate-300";

  return (
    <div ref={wrapRef} className="relative w-full overflow-hidden" style={{ height }}>
      <canvas ref={canvasRef} className="absolute inset-0" />

      {/* Title bar */}
      <div className="pointer-events-none absolute inset-x-0 top-0 flex items-center justify-between px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider">
        <div className="flex items-center gap-2 text-slate-400">
          <span className="size-1.5 animate-pulse rounded-full bg-brand-400" />
          <span className="text-brand-300">QuantML</span>
          <span className="text-slate-600">·</span>
          <span>Signal Relationship Graph</span>
        </div>
        {!compact && (
          <div className="hidden items-center gap-3 text-slate-500 sm:flex">
            <span>T+5D <span className="text-slate-300">${stats.medPrice.toFixed(2)}</span></span>
            <span>PATHS <span className="text-slate-300">2,048</span></span>
            <span>ITER <span className="text-slate-300">{iter.toLocaleString()}</span></span>
          </div>
        )}
        {compact && (
          <div className="flex items-center gap-2 text-slate-500">
            <span>Signal</span>
            <span className={callTone}>{stats.call}</span>
          </div>
        )}
      </div>

      {!compact && (
        <>
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
        </>
      )}

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

      {/* Hover tooltip */}
      {hover && hover.node.sig && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-white/10 bg-ink-900/95 px-3 py-2 shadow-panel backdrop-blur"
          style={{ left: hover.x, top: hover.y - 14 }}
        >
          <div className="flex items-center gap-2">
            <span className="size-1.5 rounded-full" style={{ background: hover.node.color }} />
            <span className="font-mono text-xs font-semibold text-white">{hover.node.sig.ticker}</span>
            <span className="font-mono text-[10px] font-bold" style={{ color: hover.node.color }}>
              {hover.node.sig.signal}
            </span>
          </div>
          <div className="mt-0.5 max-w-[160px] truncate text-[11px] text-slate-400">{hover.node.sig.company}</div>
          <div className="mt-1 flex gap-3 font-mono text-[10px] text-slate-500">
            <span>Conv <span className="text-slate-300">{hover.node.sig.confidence.toFixed(0)}%</span></span>
            <span>E[5d] <span className={hover.node.sig.expectedReturn5d >= 0 ? "text-bull-soft" : "text-bear-soft"}>{hover.node.sig.expectedReturn5d >= 0 ? "+" : ""}{hover.node.sig.expectedReturn5d.toFixed(2)}%</span></span>
          </div>
        </div>
      )}
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
function hexA(hex: string, a: number) {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}
