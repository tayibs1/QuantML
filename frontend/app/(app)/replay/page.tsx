"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Play, RotateCcw, TrendingUp, Gauge } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ReplayChart } from "@/components/charts/replay-chart";
import { api, type ReplayScenario } from "@/lib/api";
import replaySnapshot from "@/lib/snapshot/replay.json";
import { cn } from "@/lib/utils";

const INITIAL = (replaySnapshot as { scenarios: ReplayScenario[] }).scenarios;
const SPEEDS = [
  { label: "1×", ms: 130 },
  { label: "2×", ms: 60 },
];

function monthLabel(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", year: "numeric" });
}
function dayLabel(iso: string) {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

type Phase = "armed" | "playing" | "done";

export default function ReplayPage() {
  const [scenarios, setScenarios] = useState<ReplayScenario[]>(INITIAL);
  const [idx, setIdx] = useState(0);
  const sc = scenarios[idx];

  const [revealed, setRevealed] = useState(sc?.entryIndex ?? 0);
  const [phase, setPhase] = useState<Phase>("armed");
  const [speed, setSpeed] = useState(SPEEDS[0].ms);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  // Refresh from the API (same real snapshot the page is seeded with).
  useEffect(() => {
    api
      .replay()
      .then((d) => {
        if (Array.isArray(d.scenarios) && d.scenarios.length) setScenarios(d.scenarios);
      })
      .catch(() => {});
  }, []);

  const stop = useCallback(() => {
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
  }, []);

  // Reset the reveal whenever the chosen scenario changes.
  useEffect(() => {
    stop();
    setRevealed(sc?.entryIndex ?? 0);
    setPhase("armed");
  }, [idx, sc, stop]);

  // Drive the forward reveal, stopping at the exit (where P&L is realized).
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

  if (!sc) return null;

  const gain = sc.ret >= 0;
  const head = Math.min(revealed, sc.series.length - 1);
  const currentClose = sc.series[head]?.close ?? sc.entryPrice;
  const currentRet = (currentClose / sc.entryPrice - 1) * 100;
  const position = sc.pnl / (sc.ret / 100); // implied notional from the realized trade
  const currentPnl = (currentRet / 100) * position;
  const progress = Math.max(
    0,
    Math.min(1, (revealed - sc.entryIndex) / Math.max(1, sc.exitIndex - sc.entryIndex))
  );
  const started = revealed > sc.entryIndex;
  const heldDays = phase === "done" ? sc.holdDays : Math.round(progress * sc.holdDays);
  const toneText = currentRet >= 0 ? "text-bull-soft" : "text-bear-soft";

  function play() {
    if (phase === "done") setRevealed(sc.entryIndex);
    setPhase("playing");
  }

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Interactive demo"
        title="Signal Replay"
        description="A real moment from the walk-forward backtest. The model fired a signal here — press play to watch how it actually played out."
        actions={
          <Badge variant="bull" className="hidden sm:inline-flex">
            <span className="size-1.5 rounded-full bg-bull" />
            Real backtest trades
          </Badge>
        }
      />

      {/* Scenario picker — outcomes hidden so the reveal stays a surprise */}
      <div className="flex flex-wrap gap-2">
        {scenarios.map((s, i) => (
          <button
            key={s.id}
            onClick={() => setIdx(i)}
            className={cn(
              "group flex items-center gap-2.5 rounded-xl border px-3.5 py-2 text-left transition-colors",
              i === idx
                ? "border-brand-400/40 bg-brand-400/10"
                : "border-white/8 bg-white/[0.02] hover:border-white/15"
            )}
          >
            <span className="font-mono text-[11px] font-semibold text-brand-200">{s.ticker}</span>
            <span className="hidden text-sm text-slate-300 sm:block">{s.company}</span>
            <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
              {monthLabel(s.entryDate)}
            </span>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Chart + transport */}
        <GlassPanel strong className="xl:col-span-2">
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
            <div>
              <h3 className="text-sm font-semibold text-white">
                {sc.company} <span className="font-mono text-slate-500">· {sc.ticker}</span>
              </h3>
              <p className="text-[11px] text-slate-500">Daily close · {sc.sector}</p>
            </div>
            <div className="text-right">
              <div className={cn("font-mono text-lg font-semibold data", toneText)}>
                ${currentClose.toFixed(2)}
              </div>
              <div className={cn("font-mono text-[11px]", toneText)}>
                {currentRet >= 0 ? "+" : ""}
                {currentRet.toFixed(2)}% {started ? "since entry" : "at entry"}
              </div>
            </div>
          </div>

          <div className="p-4">
            <ReplayChart
              series={sc.series}
              entryIndex={sc.entryIndex}
              exitIndex={sc.exitIndex}
              revealed={revealed}
              gain={gain}
              height={360}
            />
          </div>

          {/* Transport */}
          <div className="flex flex-wrap items-center gap-3 border-t border-white/6 px-5 py-3.5">
            <Button size="sm" onClick={play} disabled={phase === "playing"}>
              {phase === "done" ? <RotateCcw className="size-4" /> : <Play className="size-4" />}
              {phase === "done" ? "Replay" : phase === "playing" ? "Playing…" : "Play"}
            </Button>
            <div className="flex items-center gap-1 rounded-lg border border-white/8 bg-white/[0.02] p-0.5">
              {SPEEDS.map((s) => (
                <button
                  key={s.label}
                  onClick={() => setSpeed(s.ms)}
                  className={cn(
                    "rounded-md px-2 py-1 font-mono text-[11px] transition-colors",
                    speed === s.ms ? "bg-brand-400/15 text-brand-200" : "text-slate-500 hover:text-slate-300"
                  )}
                >
                  {s.label}
                </button>
              ))}
            </div>
            <div className="h-1.5 min-w-[120px] flex-1 overflow-hidden rounded-full bg-white/8">
              <motion.div
                className={cn("h-full rounded-full", gain ? "bg-bull" : "bg-bear")}
                animate={{ width: `${progress * 100}%` }}
                transition={{ ease: "linear", duration: 0.1 }}
              />
            </div>
            <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
              {started ? `${heldDays}d / ${sc.holdDays}d held` : "armed"}
            </span>
          </div>
        </GlassPanel>

        {/* Signal + outcome */}
        <div className="space-y-6">
          {/* The signal the model fired at entry */}
          <GlassPanel strong>
            <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
              <Gauge className="size-4 text-brand-300" />
              <h3 className="text-sm font-semibold text-white">Model signal</h3>
            </div>
            <div className="space-y-4 p-5">
              <div className="flex items-center justify-between">
                <Badge variant="bull" className="text-[11px]">BUY</Badge>
                <span className="font-mono text-[11px] text-slate-500">{dayLabel(sc.entryDate)}</span>
              </div>

              {sc.pBuy != null && (
                <div>
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                      BUY conviction
                    </span>
                    <span className="font-mono text-xs text-brand-200">
                      {(sc.pBuy * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                    <div
                      className="h-full rounded-full bg-brand-400"
                      style={{ width: `${Math.min(100, (sc.pBuy / 0.6) * 100)}%` }}
                    />
                  </div>
                  <p className="mt-1 text-[10px] text-slate-600">vs 33% for a random 3-class call</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3 text-sm">
                <Field label="Entry price" value={`$${sc.entryPrice.toFixed(2)}`} />
                <Field label="Vol regime" value={sc.volRegime ?? "—"} />
                <Field label="Sector" value={sc.sector} />
                <Field label="Planned hold" value={`${sc.holdDays} days`} />
              </div>
            </div>
          </GlassPanel>

          {/* The outcome — ticks live during play, locks in at exit */}
          <GlassPanel strong className={cn("transition-colors", phase === "done" && (gain ? "ring-1 ring-bull/30" : "ring-1 ring-bear/30"))}>
            <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
              <TrendingUp className="size-4 text-brand-300" />
              <h3 className="text-sm font-semibold text-white">
                {phase === "done" ? "Result" : "Position P&L"}
              </h3>
            </div>
            <div className="p-5">
              <AnimatePresence mode="wait">
                {!started ? (
                  <motion.p
                    key="waiting"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="py-6 text-center text-sm text-slate-500"
                  >
                    Press <span className="text-brand-200">Play</span> to run the trade forward.
                  </motion.p>
                ) : (
                  <motion.div
                    key="pnl"
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="space-y-4"
                  >
                    <div>
                      <div className={cn("font-mono text-4xl font-bold data", toneText)}>
                        {currentRet >= 0 ? "+" : ""}
                        {currentRet.toFixed(1)}%
                      </div>
                      <div className={cn("mt-1 font-mono text-sm", toneText)}>
                        {currentPnl >= 0 ? "+" : "−"}$
                        {Math.abs(currentPnl).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <Field label="Entry" value={`$${sc.entryPrice.toFixed(2)}`} />
                      <Field
                        label={phase === "done" ? "Exit" : "Now"}
                        value={`$${currentClose.toFixed(2)}`}
                      />
                      <Field label="Held" value={`${heldDays} days`} />
                      <Field label="Exit date" value={phase === "done" ? dayLabel(sc.exitDate) : "—"} />
                    </div>
                    {phase === "done" && (
                      <p className="border-t border-white/6 pt-3 text-[11px] text-slate-500">
                        The model exited on the rebalance after {sc.holdDays} days, realizing a{" "}
                        <span className={toneText}>
                          {sc.ret >= 0 ? "+" : ""}
                          {sc.ret.toFixed(1)}%
                        </span>{" "}
                        move.
                      </p>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </GlassPanel>
        </div>
      </div>
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
