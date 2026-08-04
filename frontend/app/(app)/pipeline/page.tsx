"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  Newspaper,
  Database,
  CalendarClock,
  Sigma,
  Cpu,
  Gauge,
  TrendingUp,
  Play,
  Pause,
  RotateCcw,
  Check,
  ArrowRight,
  type LucideIcon,
} from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ReplayChart } from "@/components/charts/replay-chart";
import { HandoffSweep, ScrambleText } from "@/components/charts/signal-handoff";
import { Sparkline } from "@/components/charts/sparkline";
import replaySnapshot from "@/lib/snapshot/replay.json";
import type { ReplayScenario } from "@/lib/api";
import * as sfx from "@/lib/sfx";
import { cn } from "@/lib/utils";

const ACCENT = "#2dd4bf";

// worked example: a real BUY call from the replay set that made money
const EX: ReplayScenario = (() => {
  const all = (replaySnapshot as { scenarios: ReplayScenario[] }).scenarios;
  return all.find((s) => s.signal === "BUY" && s.correct && s.ret > 20) ?? all[0];
})();

// Each stage carries its own colour, so the walkthrough visibly warms up as raw
// data turns into a call rather than staying one flat shade throughout.
const STAGES: { id: string; label: string; icon: LucideIcon; blurb: string; accent: string }[] = [
  { id: "ingest", label: "Ingest", icon: Newspaper, blurb: "Pull prices, events and headlines", accent: "#60a5fa" },
  { id: "features", label: "Engineer", icon: Sigma, blurb: "Turn raw data into features", accent: "#a78bfa" },
  { id: "train", label: "Train", icon: Cpu, blurb: "Walk-forward model training", accent: "#fbbf24" },
  { id: "predict", label: "Predict", icon: Gauge, blurb: "Score the name", accent: "#38bdf8" },
  { id: "signal", label: "Signal", icon: TrendingUp, blurb: "The call and the payoff", accent: "#2dd4bf" },
];

const HEADLINES = [
  { src: "Newswire", time: "08:12", text: `${EX.company} guides next quarter above consensus` },
  { src: "Filings", time: "07:40", text: `Insider buying disclosed at ${EX.ticker}` },
  { src: "Sell-side", time: "06:55", text: `Two desks raise ${EX.ticker} price targets` },
  { src: "Macro", time: "06:30", text: `${EX.sector} demand indicators tick higher` },
];

// top-3 are the model's real SHAP drivers for this call; the rest fill out the vector
const FEATURES = [
  ...EX.drivers.map((name, i) => ({ name, val: 0.86 - i * 0.13, top: true })),
  { name: "ATR % of price", val: 0.44, top: false },
  { name: "Volume z-score (10d)", val: 0.57, top: false },
  { name: "RSI(14)", val: 0.63, top: false },
  { name: "Sector rel. strength", val: 0.49, top: false },
];

// Panels slide the way you're travelling. Written as variants rather than inline
// props so the leaving panel picks up the current direction too - otherwise it
// exits the wrong way whenever you step backwards.
const STAGE_SLIDE = {
  enter: (d: number) => ({ opacity: 0, x: d * 46, filter: "blur(8px)" }),
  center: { opacity: 1, x: 0, filter: "blur(0px)" },
  exit: (d: number) => ({ opacity: 0, x: d * -34, filter: "blur(8px)" }),
};

const FOLDS = [
  { train: [0, 34], test: [34, 44] },
  { train: [0, 48], test: [48, 60] },
  { train: [0, 62], test: [62, 74] },
  { train: [0, 78], test: [78, 90] },
];

export default function PipelinePage() {
  const [stage, setStage] = useState(0);
  const [playing, setPlaying] = useState(false);
  // which way the last move went, so the incoming panel enters from the side
  // you'd expect instead of every change looking identical
  const [dir, setDir] = useState(1);
  const last = STAGES.length - 1;
  const cur = STAGES[stage];

  const goTo = (next: number, viaPlay = false) => {
    setDir(next >= stage ? 1 : -1);
    setStage(next);
    if (!viaPlay) setPlaying(false);
  };

  // auto-advance while playing; stop on the final stage
  useEffect(() => {
    if (!playing) return;
    const id = setTimeout(() => {
      setStage((s) => {
        if (s >= last) {
          setPlaying(false);
          return s;
        }
        setDir(1);
        return s + 1;
      });
    }, 3400);
    return () => clearTimeout(id);
  }, [playing, stage, last]);

  // Sound follows the stage rather than the click, so jumping around with the
  // stepper sounds the same as letting the walkthrough run. No-ops when sound
  // is off. The one on arrival is skipped.
  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    if (stage >= last) sfx.complete();
    else sfx.stage(stage, STAGES.length);
  }, [stage, last]);

  function toggle() {
    if (stage >= last) {
      setDir(1);
      setStage(0);
      setPlaying(true);
    } else {
      setPlaying((p) => !p);
    }
  }

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="How it works"
        title="Signal Pipeline"
        description="Follow one real call end to end — from the raw data that comes in, through the features and model, to the signal and the profit it captured."
        actions={
          <Button size="sm" onClick={toggle}>
            {playing ? <Pause className="size-4" /> : stage >= last ? <RotateCcw className="size-4" /> : <Play className="size-4" />}
            {playing ? "Pause" : stage >= last ? "Replay" : "Play walkthrough"}
          </Button>
        }
      />

      {/* Stepper */}
      <div className="flex items-center">
        {STAGES.map((s, i) => {
          const Icon = s.icon;
          const active = i === stage;
          const doneStep = i < stage;
          return (
            <div key={s.id} className="flex flex-1 items-center last:flex-none">
              {/* silent because changing stage plays its own cue */}
              <button
                onClick={() => goTo(i)}
                data-silent="true"
                className="flex flex-col items-center gap-1.5 text-center"
              >
                <motion.span
                  animate={
                    active
                      ? { scale: 1.12, borderColor: `${s.accent}80`, boxShadow: `0 0 22px -4px ${s.accent}` }
                      : { scale: 1, borderColor: "rgba(255,255,255,0.08)", boxShadow: "0 0 0 0 transparent" }
                  }
                  transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  style={active ? { color: s.accent, background: `${s.accent}1f` } : undefined}
                  className={cn(
                    "flex size-10 items-center justify-center rounded-xl border",
                    !active && (doneStep
                      ? "border-brand-400/25 bg-brand-500/10 text-brand-300"
                      : "border-white/8 bg-white/[0.02] text-slate-500")
                  )}
                >
                  {doneStep ? <Check className="size-4" /> : <Icon className="size-4" />}
                </motion.span>
                <span className={cn("font-mono text-[10px] uppercase tracking-wider", active ? "text-white" : "text-slate-500")}>
                  {s.label}
                </span>
              </button>
              {i < last && (
                <div className="relative mx-2 mb-5 h-px flex-1 overflow-hidden rounded bg-white/8">
                  <motion.div
                    className="h-full rounded"
                    style={{ background: s.accent }}
                    initial={false}
                    animate={{ width: i < stage ? "100%" : "0%" }}
                    transition={{ duration: 0.5 }}
                  />
                  {/* A packet running down the wire into the stage that's about to
                      open, so the walkthrough reads as data moving along. */}
                  {i === stage - 1 && (
                    <motion.span
                      key={`packet-${stage}`}
                      className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full"
                      style={{ background: STAGES[i + 1].accent, boxShadow: `0 0 10px 2px ${STAGES[i + 1].accent}` }}
                      initial={{ left: "0%", opacity: 0 }}
                      animate={{ left: "100%", opacity: [0, 1, 1, 0] }}
                      transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
                    />
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Stage viewport */}
      <GlassPanel strong className="relative overflow-hidden">
        {/* Same light-bar wipe the replay page uses, tinted to the stage. */}
        <HandoffSweep id={cur.id} accent={cur.accent} />

        <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
          <div className="flex items-center gap-2.5">
            <motion.span
              key={`n-${stage}`}
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: "spring", stiffness: 380, damping: 18 }}
              style={{ color: cur.accent, background: `${cur.accent}26` }}
              className="rounded-md px-2 py-0.5 font-mono text-[11px] font-bold"
            >
              {stage + 1}/{STAGES.length}
            </motion.span>
            <h3 className="text-sm font-semibold text-white">
              <ScrambleText text={cur.blurb} trigger={cur.id} />
            </h3>
          </div>
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">
            Example · {EX.ticker}
          </span>
        </div>

        {/* A thin bar showing how long the current stage holds before the
            walkthrough moves on, so the pacing is visible rather than a surprise. */}
        <div className="h-px w-full bg-white/5">
          {playing && (
            <motion.div
              key={`t-${stage}`}
              className="h-full"
              style={{ background: cur.accent }}
              initial={{ width: "0%" }}
              animate={{ width: "100%" }}
              transition={{ duration: 3.4, ease: "linear" }}
            />
          )}
        </div>

        <div className="min-h-[420px] p-5">
          <AnimatePresence mode="wait" custom={dir}>
            <motion.div
              key={stage}
              custom={dir}
              variants={STAGE_SLIDE}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.42, ease: [0.22, 1, 0.36, 1] }}
            >
              {stage === 0 && <Ingest />}
              {stage === 1 && <Engineer />}
              {stage === 2 && <Train />}
              {stage === 3 && <Predict />}
              {stage === 4 && <SignalStage />}
            </motion.div>
          </AnimatePresence>
        </div>
      </GlassPanel>

      <p className="text-[11px] leading-relaxed text-slate-600">
        A single call walked end to end. Headlines shown are illustrative; the model itself is trained on price,
        volatility, volume and event features. Full methodology and out-of-sample numbers live on the Validation page.
      </p>
    </PageTransition>
  );
}

// ── Stage 0: ingest ──────────────────────────────────────────────────────────
function Ingest() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Source icon={Database} title="Market data" caption="Daily OHLCV for 100 names">
        <div className="mt-3 h-16">
          <Sparkline id="ingest-px" data={EX.series.slice(0, 26).map((p) => ({ v: p.value }))} color={ACCENT} height={64} />
        </div>
        <div className="mt-2 grid grid-cols-4 gap-2 font-mono text-[10px] text-slate-500">
          {["O", "H", "L", "C"].map((k) => (
            <div key={k} className="rounded bg-white/[0.03] px-1.5 py-1 text-center">
              <span className="text-slate-600">{k}</span>{" "}
              <span className="text-slate-300">{(EX.entryPrice * (0.98 + Math.random() * 0.04)).toFixed(0)}</span>
            </div>
          ))}
        </div>
      </Source>

      <Source icon={Newspaper} title="News & headlines" caption="Scanned for events">
        <div className="mt-3 space-y-2">
          {HEADLINES.map((h, i) => (
            <motion.div
              key={h.text}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 + i * 0.12 }}
              className="rounded-lg border border-white/6 bg-white/[0.02] px-2.5 py-1.5"
            >
              <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
                <span className="text-brand-300">{h.src}</span>
                <span>·</span>
                <span>{h.time}</span>
              </div>
              <div className="mt-0.5 text-[12px] leading-snug text-slate-300">{h.text}</div>
            </motion.div>
          ))}
        </div>
      </Source>

      <Source icon={CalendarClock} title="Events & calendar" caption="Earnings, splits, filings">
        <div className="mt-3 space-y-2 text-[12px]">
          <Row k="Next earnings" v="in 9 days" />
          <Row k="Sector" v={EX.sector} />
          <Row k="Vol regime" v={EX.volRegime ?? "—"} />
          <Row k="Universe" v="NASDAQ 100" />
        </div>
      </Source>
    </div>
  );
}

// ── Stage 1: features ────────────────────────────────────────────────────────
function Engineer() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <p className="text-sm text-slate-400">
          The quantifiable inputs — price action, volatility, volume and events — are turned into{" "}
          <span className="text-white">~24 numeric features</span> per name, using only information available on
          the signal date (no lookahead).
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {["Momentum", "Volatility", "Mean-reversion", "Volume", "Events"].map((t) => (
            <span key={t} className="rounded-full border border-white/8 bg-white/[0.02] px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider text-slate-400">
              {t}
            </span>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">Feature vector · {EX.ticker}</div>
        {FEATURES.map((f, i) => (
          <div key={f.name} className="flex items-center gap-3">
            <span className={cn("w-40 shrink-0 truncate text-[12px]", f.top ? "text-slate-200" : "text-slate-500")}>{f.name}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/8">
              <motion.div
                className={cn("h-full rounded-full", f.top ? "bg-brand-400" : "bg-slate-600")}
                initial={{ width: 0 }}
                animate={{ width: `${f.val * 100}%` }}
                transition={{ delay: i * 0.06, duration: 0.5 }}
              />
            </div>
            <span className="w-10 text-right font-mono text-[11px] text-slate-500 data">{f.val.toFixed(2)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Stage 2: training ────────────────────────────────────────────────────────
function Train() {
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div>
        <p className="text-sm text-slate-400">
          An <span className="text-white">XGBoost</span> model is retrained <span className="text-white">walk-forward</span>:
          each fold trains only on the past and is tested on the untouched future, so the score reflects out-of-sample skill.
        </p>
        <div className="mt-5 space-y-2.5">
          {FOLDS.map((f, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="w-12 font-mono text-[10px] uppercase tracking-wider text-slate-500">Fold {i + 1}</span>
              <div className="relative h-4 flex-1 overflow-hidden rounded bg-white/[0.03]">
                <motion.div
                  className="absolute inset-y-0 rounded bg-brand-500/25"
                  initial={{ width: 0 }}
                  animate={{ left: `${f.train[0]}%`, width: `${f.train[1] - f.train[0]}%` }}
                  transition={{ delay: i * 0.15, duration: 0.5 }}
                />
                <motion.div
                  className="absolute inset-y-0 rounded bg-brand-400"
                  initial={{ opacity: 0 }}
                  animate={{ left: `${f.test[0]}%`, width: `${f.test[1] - f.test[0]}%`, opacity: 1 }}
                  transition={{ delay: 0.3 + i * 0.15, duration: 0.4 }}
                />
              </div>
            </div>
          ))}
          <div className="flex gap-4 pt-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
            <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-brand-500/40" /> Train</span>
            <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-brand-400" /> Test</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 self-start">
        <TrainStat label="Walk-forward Sharpe" to={1.19} decimals={2} />
        <TrainStat label="Out-of-sample AUC" to={0.54} decimals={3} />
        <TrainStat label="BUY hit rate" to={52.8} decimals={1} suffix="%" />
        <TrainStat label="Folds" to={6} decimals={0} />
      </div>
    </div>
  );
}

function TrainStat({ label, to, decimals, suffix = "" }: { label: string; to: number; decimals: number; suffix?: string }) {
  const [v, setV] = useState(0);
  useEffect(() => {
    const t0 = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const k = Math.min(1, (t - t0) / 900);
      setV(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to]);
  return (
    <GlassPanel inset className="py-3">
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-1 font-mono text-xl font-semibold text-white data">{v.toFixed(decimals)}{suffix}</div>
    </GlassPanel>
  );
}

// ── Stage 3: predict ─────────────────────────────────────────────────────────
function Predict() {
  const conv = EX.conviction;
  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <div className="flex flex-col items-center justify-center">
        <div className="relative flex size-44 items-center justify-center">
          <svg viewBox="0 0 120 120" className="size-44 -rotate-90">
            <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="10" />
            <motion.circle
              cx="60" cy="60" r="52" fill="none" stroke={ACCENT} strokeWidth="10" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 52}
              initial={{ strokeDashoffset: 2 * Math.PI * 52 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 52 * (1 - conv / 100) }}
              transition={{ duration: 1, ease: "easeOut" }}
            />
          </svg>
          <div className="absolute text-center">
            <div className="font-mono text-3xl font-bold text-white data">{conv.toFixed(0)}%</div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">conviction</div>
          </div>
        </div>
        <div className="mt-4 flex items-center gap-2">
          <span className="font-mono text-[11px] text-slate-500">P(outperform)</span>
          <span className="font-mono text-sm text-brand-200">{(conv / 100).toFixed(2)}</span>
          <ArrowRight className="size-3.5 text-slate-600" />
          <span className="rounded-md bg-bull/15 px-2 py-0.5 font-mono text-xs font-bold text-bull-soft">BUY</span>
        </div>
      </div>

      <div>
        <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">Top drivers (SHAP)</div>
        <div className="mt-3 space-y-2.5">
          {EX.drivers.map((d, i) => (
            <motion.div
              key={d}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
              className="flex items-center gap-2.5 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"
            >
              <span className="font-mono text-[10px] text-slate-600">{i + 1}</span>
              <span className="size-1.5 rounded-full bg-brand-400" />
              <span className="text-sm text-slate-200">{d}</span>
            </motion.div>
          ))}
        </div>
        <p className="mt-4 text-[12px] leading-relaxed text-slate-500">
          The model maps the feature vector to a probability the name beats QQQ over the next {EX.holdDays} days.
          Above the BUY threshold, so the call is <span className="text-bull-soft">BUY</span> at {conv.toFixed(0)}% conviction.
        </p>
      </div>
    </div>
  );
}

// ── Stage 4: signal + profit ─────────────────────────────────────────────────
function SignalStage() {
  const [revealed, setRevealed] = useState(EX.entryIndex);
  useEffect(() => {
    const id = setInterval(() => {
      setRevealed((r) => {
        if (r >= EX.exitIndex) {
          clearInterval(id);
          return r;
        }
        return r + 1;
      });
    }, 80);
    return () => clearInterval(id);
  }, []);
  const done = revealed >= EX.exitIndex;

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <ReplayChart
          series={EX.series}
          entryIndex={EX.entryIndex}
          exitIndex={EX.exitIndex}
          revealed={revealed}
          accent={ACCENT}
          height={300}
        />
      </div>
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-bull/15 px-2 py-0.5 font-mono text-[11px] font-bold text-bull-soft">BUY</span>
          <span className="text-sm font-semibold text-white">{EX.company}</span>
          <span className="font-mono text-slate-500">· {EX.ticker}</span>
        </div>
        <div>
          <div className="font-mono text-4xl font-bold text-bull-soft data">+{EX.ret.toFixed(1)}%</div>
          <div className="mt-1 font-mono text-sm text-slate-400">
            ${EX.notional.toLocaleString()} → <span className="text-bull-soft">${EX.endValue.toLocaleString()}</span>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3 border-t border-white/6 pt-3 text-sm">
          <Row k="vs QQQ" v={`+${(EX.benchRet ?? 0).toFixed(1)}%`} />
          <Row k="Held" v={`${EX.holdDays} days`} />
          <Row k="Conviction" v={`${EX.conviction.toFixed(0)}%`} />
          <Row k="Regime" v={EX.volRegime ?? "—"} />
        </div>
        {done && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-1.5 rounded-lg bg-bull/10 px-3 py-2">
            <Check className="size-3.5 text-bull-soft" />
            <span className="text-[12px] text-bull-soft">Called it — beat the benchmark by {(EX.ret - (EX.benchRet ?? 0)).toFixed(1)} pts.</span>
          </motion.div>
        )}
      </div>
    </div>
  );
}

// ── shared bits ──────────────────────────────────────────────────────────────
function Source({ icon: Icon, title, caption, children }: { icon: LucideIcon; title: string; caption: string; children: React.ReactNode }) {
  return (
    <GlassPanel inset className="h-full">
      <div className="flex items-center gap-2">
        <Icon className="size-4 text-brand-300" />
        <div>
          <div className="text-sm font-semibold text-white">{title}</div>
          <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{caption}</div>
        </div>
      </div>
      {children}
    </GlassPanel>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{k}</span>
      <span className="text-slate-200">{v}</span>
    </div>
  );
}
