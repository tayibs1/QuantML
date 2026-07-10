"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Play, RotateCcw, Sparkles, Check, X, Cpu } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { ReplayChart } from "@/components/charts/replay-chart";
import { SignalGraph } from "@/components/charts/signal-graph";
import { api, type ReplayScenario, type SignalType } from "@/lib/api";
import replaySnapshot from "@/lib/snapshot/replay.json";
import signalsSnapshot from "@/lib/snapshot/signals.json";
import { cn } from "@/lib/utils";

const GRAPH_SIGNALS = signalsSnapshot as Parameters<typeof SignalGraph>[0]["signals"];

const INITIAL = (replaySnapshot as { scenarios: ReplayScenario[] }).scenarios;
const SPEEDS = [
  { label: "1×", ms: 140 },
  { label: "2×", ms: 65 },
];
const FILTERS: (SignalType | "ALL")[] = ["ALL", "BUY", "HOLD", "AVOID"];

const SIG: Record<SignalType, { accent: string; chip: string; text: string; bar: string; dot: string }> = {
  BUY: { accent: "#2dd4bf", chip: "bg-bull/15 text-bull-soft", text: "text-bull-soft", bar: "bg-bull", dot: "bg-bull" },
  HOLD: { accent: "#fbbf24", chip: "bg-amber-400/15 text-amber-300", text: "text-amber-300", bar: "bg-amber-400", dot: "bg-amber-400" },
  AVOID: { accent: "#f87171", chip: "bg-bear/15 text-bear-soft", text: "text-bear-soft", bar: "bg-bear", dot: "bg-bear" },
};

function monthLabel(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}
function dayLabel(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}
function pct(n: number) {
  return `${n >= 0 ? "+" : ""}${n.toFixed(1)}%`;
}

type Phase = "armed" | "playing" | "done";

export default function ReplayPage() {
  const [all, setAll] = useState<ReplayScenario[]>(INITIAL);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("ALL");
  const scenarios = filter === "ALL" ? all : all.filter((s) => s.signal === filter);

  const [idx, setIdx] = useState(0);
  const sc = scenarios[Math.min(idx, scenarios.length - 1)];

  const [revealed, setRevealed] = useState(sc?.entryIndex ?? 0);
  const [phase, setPhase] = useState<Phase>("armed");
  const [speed, setSpeed] = useState(SPEEDS[0].ms);
  const [tour, setTour] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const tourTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    api
      .replay()
      .then((d) => Array.isArray(d.scenarios) && d.scenarios.length && setAll(d.scenarios))
      .catch(() => {});
  }, []);

  const stop = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }, []);

  useEffect(() => setIdx(0), [filter]);

  // Reset when the scenario changes; if touring, auto-start after a beat.
  useEffect(() => {
    stop();
    setRevealed(sc?.entryIndex ?? 0);
    setPhase("armed");
    if (tour && sc) {
      tourTimer.current = setTimeout(() => setPhase("playing"), 1400);
      return () => {
        if (tourTimer.current) clearTimeout(tourTimer.current);
      };
    }
  }, [idx, sc, tour, stop]);

  // Drive the forward reveal to the exit.
  useEffect(() => {
    if (phase !== "playing" || !sc) return;
    timer.current = setInterval(() => {
      setRevealed((r) => {
        if (r >= sc.exitIndex) {
          stop();
          setPhase("done");
          return sc.exitIndex;
        }
        return r + 1;
      });
    }, speed);
    return stop;
  }, [phase, sc, speed, stop]);

  // Tour: after the reveal lands, pause on the result, then advance.
  useEffect(() => {
    if (!tour || phase !== "done") return;
    tourTimer.current = setTimeout(() => {
      setIdx((i) => (i + 1) % scenarios.length);
    }, 2600);
    return () => {
      if (tourTimer.current) clearTimeout(tourTimer.current);
    };
  }, [tour, phase, scenarios.length]);

  if (!sc) return null;

  const sig = SIG[sc.signal];
  const head = Math.min(revealed, sc.series.length - 1);
  const done = phase === "done";
  const started = revealed > sc.entryIndex;
  const liveRet = (sc.series[head]?.value ?? 100) - 100;
  const ret = done ? sc.ret : liveRet;
  const benchRet = done ? sc.benchRet ?? 0 : (sc.series[head]?.bench ?? 100) - 100;
  const dollar = done ? sc.endValue : Math.round((sc.notional * (sc.series[head]?.value ?? 100)) / 100);
  const curPrice = done ? sc.exitPrice : sc.entryPrice * (1 + ret / 100);
  const retTone = ret >= 0 ? "text-bull-soft" : "text-bear-soft";
  const progress = Math.max(0, Math.min(1, (revealed - sc.entryIndex) / Math.max(1, sc.exitIndex - sc.entryIndex)));
  const heldDays = done ? sc.holdDays : Math.round(progress * sc.holdDays);

  function play() {
    if (done) setRevealed(sc.entryIndex);
    setPhase("playing");
  }
  function toggleTour() {
    if (tour) {
      setTour(false);
      stop();
    } else {
      setTour(true);
      play();
    }
  }

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Interactive demo"
        title="Signal Replay"
        description="QuantML scores every NASDAQ-100 name as BUY, HOLD, or AVOID. Pick a call, see the model's reasoning, then press play to watch what happened next."
        actions={
          <Button size="sm" variant={tour ? "primary" : "outline"} onClick={toggleTour}>
            <Sparkles className="size-4" />
            {tour ? "Stop tour" : "Auto-play tour"}
          </Button>
        }
      />

      {/* Class filter */}
      <div className="flex flex-wrap items-center gap-2">
        <div className="flex items-center gap-1 rounded-lg border border-white/8 bg-white/[0.02] p-0.5">
          {FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={cn(
                "rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-wider transition-colors",
                filter === f ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
              )}
            >
              {f}
            </button>
          ))}
        </div>
        <span className="font-mono text-[10px] text-slate-600">
          {scenarios.length} {scenarios.length === 1 ? "call" : "calls"}
        </span>
      </div>

      {/* Scenario picker — colour = the model's call, outcome hidden */}
      <div className="flex flex-wrap gap-2">
        {scenarios.map((s, i) => {
          const c = SIG[s.signal];
          return (
            <button
              key={s.id}
              onClick={() => setIdx(i)}
              className={cn(
                "flex items-center gap-2.5 rounded-xl border px-3.5 py-2 transition-colors",
                i === idx ? "border-white/20 bg-white/[0.05]" : "border-white/8 bg-white/[0.02] hover:border-white/15"
              )}
            >
              <span className={cn("size-1.5 rounded-full", c.dot)} />
              <span className="font-mono text-[11px] font-semibold text-slate-200">{s.ticker}</span>
              <span className="hidden text-sm text-slate-400 sm:block">{s.company}</span>
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-600">
                {monthLabel(s.entryDate)}
              </span>
            </button>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Chart + transport */}
        <GlassPanel strong className="xl:col-span-2">
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
            <div className="flex items-center gap-2.5">
              <span className={cn("rounded-md px-2 py-0.5 font-mono text-[11px] font-bold", sig.chip)}>
                {sc.signal}
              </span>
              <div>
                <h3 className="text-sm font-semibold text-white">
                  {sc.company} <span className="font-mono text-slate-500">· {sc.ticker}</span>
                </h3>
                <p className="text-[11px] text-slate-500">Rebased to 100 at the signal · vs QQQ</p>
              </div>
            </div>
            <div className="text-right">
              <div className={cn("font-mono text-lg font-semibold data", retTone)}>{pct(ret)}</div>
              <div className="font-mono text-[11px] text-slate-500">QQQ {pct(benchRet)}</div>
            </div>
          </div>

          <div className="p-4">
            <ReplayChart
              series={sc.series}
              entryIndex={sc.entryIndex}
              exitIndex={sc.exitIndex}
              revealed={revealed}
              accent={sig.accent}
              height={380}
            />
          </div>

          <div className="flex flex-wrap items-center gap-3 border-t border-white/6 px-5 py-3.5">
            <Button size="sm" onClick={play} disabled={phase === "playing"}>
              {done ? <RotateCcw className="size-4" /> : <Play className="size-4" />}
              {done ? "Replay" : phase === "playing" ? "Playing…" : "Play"}
            </Button>
            <div className="flex items-center gap-1 rounded-lg border border-white/8 bg-white/[0.02] p-0.5">
              {SPEEDS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => setSpeed(s.ms)}
                  className={cn(
                    "rounded-md px-2 py-1 font-mono text-[11px] transition-colors",
                    speed === s.ms ? "bg-white/10 text-white" : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="h-1.5 min-w-[100px] flex-1 overflow-hidden rounded-full bg-white/8">
              <motion.div
                className={cn("h-full rounded-full", sig.bar)}
                animate={{ width: `${progress * 100}%` }}
                transition={{ ease: "linear", duration: 0.1 }}
              />
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
              {started ? `${heldDays}d / ${sc.holdDays}d` : "armed"}
            </span>
          </div>
        </GlassPanel>

        {/* Signal reasoning + outcome */}
        <div className="space-y-6">
          <GlassPanel strong>
            <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
              <Cpu className="size-4 text-brand-300" />
              <h3 className="text-sm font-semibold text-white">Why the model called it</h3>
            </div>
            <div className="space-y-4 p-5">
              <div className="flex items-center justify-between">
                <span className={cn("rounded-md px-2.5 py-1 font-mono text-sm font-bold", sig.chip)}>
                  {sc.signal}
                </span>
                <span className="font-mono text-[11px] text-slate-500">{dayLabel(sc.entryDate)}</span>
              </div>

              <div>
                <div className="mb-1.5 flex items-center justify-between">
                  <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">Conviction</span>
                  <span className="font-mono text-xs text-slate-300">{sc.conviction.toFixed(0)}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                  <div className={cn("h-full rounded-full", sig.bar)} style={{ width: `${sc.conviction}%` }} />
                </div>
              </div>

              <div>
                <div className="mb-2 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                  Top drivers (SHAP)
                </div>
                <div className="space-y-1.5">
                  {sc.drivers.map((d, i) => (
                    <div key={d} className="flex items-center gap-2 text-sm text-slate-300">
                      <span className="font-mono text-[10px] text-slate-600">{i + 1}</span>
                      <span className={cn("size-1 rounded-full", sig.dot)} />
                      {d}
                    </div>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 border-t border-white/6 pt-3 text-sm">
                <Field label="Sector" value={sc.sector} />
                <Field label="Vol regime" value={sc.volRegime ?? "—"} />
              </div>
            </div>
          </GlassPanel>

          <GlassPanel strong className={cn("transition-all", done && (sc.correct ? "ring-1 ring-bull/30" : "ring-1 ring-bear/30"))}>
            <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
              <h3 className="text-sm font-semibold text-white">{done ? "Outcome" : "Live P&L"}</h3>
              {done && (
                <span
                  className={cn(
                    "flex items-center gap-1 rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold",
                    sc.correct ? "bg-bull/15 text-bull-soft" : "bg-bear/15 text-bear-soft"
                  )}
                >
                  {sc.correct ? <Check className="size-3" /> : <X className="size-3" />}
                  {sc.correct ? "Called it" : "Missed"}
                </span>
              )}
            </div>
            <div className="p-5">
              <AnimatePresence mode="wait">
                {!started ? (
                  <motion.p key="wait" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="py-6 text-center text-sm text-slate-500">
                    Press <span className="text-brand-200">Play</span> to run the next {sc.holdDays} trading days.
                  </motion.p>
                ) : (
                  <motion.div key="out" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                    <div>
                      <div className={cn("font-mono text-4xl font-bold data", retTone)}>{pct(ret)}</div>
                      <div className="mt-1 font-mono text-sm text-slate-400">
                        ${sc.notional.toLocaleString()} → <span className={retTone}>${dollar.toLocaleString()}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <Field label="vs QQQ" value={pct(benchRet)} />
                      <Field label="Held" value={`${heldDays} days`} />
                      <Field label="Entry" value={`$${sc.entryPrice.toFixed(2)}`} />
                      <Field label={done ? "Exit" : "Now"} value={`$${curPrice.toFixed(2)}`} />
                    </div>
                    {done && (
                      <p className="border-t border-white/6 pt-3 text-[11px] leading-relaxed text-slate-500">
                        {sc.company} {sc.verdictVerb} over the next {sc.holdDays} trading days
                        {" "}({pct(sc.ret)} vs QQQ {pct(sc.benchRet ?? 0)}). The model called{" "}
                        <span className={sig.text}>{sc.signal}</span> — {sc.correct ? "a correct read." : "and got this one wrong."}
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </GlassPanel>
        </div>
      </div>

      <p className="text-[11px] leading-relaxed text-slate-600">
        The production model applied to historical setups, to show how it reasons. Picks span all three
        signals and include honest misses. For rigorous walk-forward, out-of-sample performance, see the
        Backtests and Validation pages.
      </p>
    </PageTransition>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-0.5 text-slate-200">{value}</div>
    </div>
  );
}
