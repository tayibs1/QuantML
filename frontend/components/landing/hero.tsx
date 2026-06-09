"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowRight, LineChart, Sparkles, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { HeroBackground } from "@/components/landing/hero-background";
import { Button } from "@/components/ui/button";
import { GlassPanel } from "@/components/glass-panel";
import { ConfidenceRing } from "@/components/confidence-ring";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import { equitySeriesShort } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const ease = [0.21, 0.6, 0.35, 1] as const;

const CHIPS = [
  { ticker: "NVDA", signal: "BUY", conf: 78, Icon: TrendingUp, tone: "bull" },
  { ticker: "TSLA", signal: "AVOID", conf: 71, Icon: TrendingDown, tone: "bear" },
  { ticker: "MSFT", signal: "HOLD", conf: 54, Icon: Minus, tone: "hold" },
] as const;

function FloatingChip({
  chip,
  className,
  delay,
}: {
  chip: (typeof CHIPS)[number];
  className?: string;
  delay: number;
}) {
  const Icon = chip.Icon;
  const tone = {
    bull: "border-bull/30 text-bull-soft",
    bear: "border-bear/30 text-bear-soft",
    hold: "border-hold/30 text-hold-soft",
  }[chip.tone];

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85, y: 14 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ duration: 0.6, delay, ease }}
      className={cn("absolute hidden lg:block", className)}
    >
      <motion.div
        animate={{ y: [0, -12, 0] }}
        transition={{ duration: 6, repeat: Infinity, ease: "easeInOut", delay }}
        className="glass-strong flex items-center gap-3 rounded-2xl px-4 py-3 shadow-panel"
      >
        <span className="text-sm font-semibold text-white">{chip.ticker}</span>
        <span
          className={cn(
            "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-[10px]",
            tone
          )}
        >
          <Icon className="size-3" />
          {chip.signal}
        </span>
        <div className="flex items-center gap-1.5">
          <div className="h-1 w-10 overflow-hidden rounded-full bg-white/10">
            <div
              className="h-full rounded-full bg-brand-400"
              style={{ width: `${chip.conf}%` }}
            />
          </div>
          <span className="font-mono text-[10px] text-slate-400">{chip.conf}%</span>
        </div>
      </motion.div>
    </motion.div>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden pb-20 pt-36 sm:pt-44">
      <HeroBackground />

      {/* Floating signal chips */}
      <FloatingChip chip={CHIPS[0]} className="left-[6%] top-[28%]" delay={0.5} />
      <FloatingChip chip={CHIPS[1]} className="right-[7%] top-[34%]" delay={0.7} />
      <FloatingChip chip={CHIPS[2]} className="left-[10%] top-[62%]" delay={0.9} />

      <div className="relative mx-auto max-w-4xl px-6 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease }}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5 backdrop-blur"
        >
          <span className="flex size-1.5">
            <span className="size-1.5 animate-pulse rounded-full bg-brand-400" />
          </span>
          <span className="font-mono text-[11px] uppercase tracking-[0.18em] text-slate-300">
            ML Research · Backtesting · RAG Intelligence
          </span>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.08, ease }}
          className="mt-7 text-5xl font-semibold leading-[1.05] tracking-tight text-white sm:text-7xl"
        >
          Quant<span className="text-gradient-brand">ML</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.16, ease }}
          className="mx-auto mt-5 max-w-2xl text-balance text-lg text-slate-300 sm:text-xl"
        >
          A production ML research platform for{" "}
          <span className="text-white">trading signals</span>,{" "}
          <span className="text-white">risk-aware backtesting</span>, and{" "}
          <span className="text-white">RAG-based market analysis</span>.
        </motion.p>

        <motion.p
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.24, ease }}
          className="mx-auto mt-4 max-w-2xl text-sm leading-relaxed text-slate-500"
        >
          Develop, evaluate, and explain machine-learning trading strategies with
          realistic costs, walk-forward validation, model monitoring, and
          AI-powered research intelligence.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.32, ease }}
          className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row"
        >
          <Button asChild size="lg" className="w-full sm:w-auto">
            <Link href="/dashboard">
              Launch Dashboard <ArrowRight className="size-4" />
            </Link>
          </Button>
          <Button asChild variant="secondary" size="lg" className="w-full sm:w-auto">
            <Link href="/backtests">
              <LineChart className="size-4" /> View Backtest Results
            </Link>
          </Button>
        </motion.div>
      </div>

      {/* Hero terminal preview */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, delay: 0.4, ease }}
        className="relative mx-auto mt-16 max-w-5xl px-6"
      >
        <div className="absolute inset-x-12 -top-6 h-24 bg-brand-500/20 blur-3xl" />
        <GlassPanel strong className="relative p-2 sm:p-3">
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            {/* Equity preview */}
            <div className="rounded-xl border border-white/6 bg-ink-950/40 p-4 lg:col-span-2">
              <div className="mb-3 flex items-center justify-between">
                <div>
                  <p className="text-xs font-medium text-slate-300">
                    Strategy Equity · vs QQQ
                  </p>
                  <p className="font-mono text-[10px] text-slate-500">
                    walk-forward · net of costs
                  </p>
                </div>
                <span className="inline-flex items-center gap-1 rounded-md bg-bull/10 px-2 py-0.5 font-mono text-[11px] text-bull-soft">
                  <TrendingUp className="size-3" /> +28.4%
                </span>
              </div>
              <EquityCurveChart data={equitySeriesShort} height={180} />
            </div>

            {/* Confidence + signals */}
            <div className="space-y-3">
              <div className="flex items-center gap-4 rounded-xl border border-white/6 bg-ink-950/40 p-4">
                <ConfidenceRing value={78} size={64} stroke={6} />
                <div>
                  <p className="text-xs text-slate-400">Model Confidence</p>
                  <p className="mt-0.5 text-lg font-semibold text-white">High</p>
                  <p className="font-mono text-[10px] text-slate-500">
                    XGBoost-v3 · drift low
                  </p>
                </div>
              </div>
              <div className="space-y-2 rounded-xl border border-white/6 bg-ink-950/40 p-3">
                {CHIPS.map((c) => {
                  const Icon = c.Icon;
                  const tone = {
                    bull: "text-bull-soft",
                    bear: "text-bear-soft",
                    hold: "text-hold-soft",
                  }[c.tone];
                  return (
                    <div key={c.ticker} className="flex items-center gap-2 text-sm">
                      <span className="w-12 font-semibold text-white">
                        {c.ticker}
                      </span>
                      <Icon className={cn("size-3.5", tone)} />
                      <span className={cn("font-mono text-xs", tone)}>
                        {c.signal}
                      </span>
                      <span className="ml-auto font-mono text-xs text-slate-500">
                        {c.conf}%
                      </span>
                    </div>
                  );
                })}
              </div>
              <Link
                href="/research"
                className="flex items-center justify-center gap-2 rounded-xl border border-violet/25 bg-violet/[0.07] py-2.5 text-sm font-medium text-violet-200 transition-colors hover:bg-violet/[0.12]"
              >
                <Sparkles className="size-4" /> Ask Research AI
              </Link>
            </div>
          </div>
        </GlassPanel>
      </motion.div>
    </section>
  );
}
