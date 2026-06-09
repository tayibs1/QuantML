"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { Sparkles, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { GlassPanel } from "./glass-panel";
import { Badge } from "./ui/badge";
import { ConfidenceRing } from "./confidence-ring";
import type { Signal } from "@/lib/mock-data";
import { cn, formatSignedPct } from "@/lib/utils";

const SIGNAL_STYLES = {
  BUY: {
    badge: "bull" as const,
    ring: "#22c55e",
    glow: "hover:shadow-[0_0_0_1px_rgba(34,197,94,0.18),0_0_44px_-10px_rgba(34,197,94,0.45)]",
    Icon: TrendingUp,
    bar: "from-bull/60 to-bull/0",
  },
  HOLD: {
    badge: "hold" as const,
    ring: "#f59e0b",
    glow: "hover:shadow-[0_0_0_1px_rgba(245,158,11,0.18),0_0_44px_-10px_rgba(245,158,11,0.4)]",
    Icon: Minus,
    bar: "from-hold/60 to-hold/0",
  },
  AVOID: {
    badge: "bear" as const,
    ring: "#f43f5e",
    glow: "hover:shadow-[0_0_0_1px_rgba(244,63,94,0.18),0_0_44px_-10px_rgba(244,63,94,0.45)]",
    Icon: TrendingDown,
    bar: "from-bear/60 to-bear/0",
  },
};

const RISK_TONE: Record<string, string> = {
  Low: "text-bull-soft",
  Moderate: "text-hold-soft",
  High: "text-bear-soft",
  Elevated: "text-bear-soft",
};

export function SignalCard({ signal, index = 0 }: { signal: Signal; index?: number }) {
  const s = SIGNAL_STYLES[signal.signal];
  const Icon = s.Icon;

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.06, ease: [0.21, 0.6, 0.35, 1] }}
      whileHover={{ y: -6 }}
      className="group"
    >
      <GlassPanel
        strong
        className={cn(
          "relative h-full p-5 transition-shadow duration-300",
          s.glow
        )}
      >
        {/* Accent bar */}
        <div
          className={cn(
            "absolute inset-x-0 top-0 h-px bg-gradient-to-r",
            s.bar
          )}
        />

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold tracking-tight text-white">
                {signal.ticker}
              </span>
              <span
                className={cn(
                  "font-mono text-xs",
                  signal.change >= 0 ? "text-bull-soft" : "text-bear-soft"
                )}
              >
                {formatSignedPct(signal.change)}
              </span>
            </div>
            <p className="mt-0.5 truncate text-xs text-slate-500">
              {signal.company} · {signal.sector}
            </p>
          </div>

          <ConfidenceRing value={signal.confidence} color={s.ring} />
        </div>

        <div className="mt-4 flex items-center gap-2">
          <Badge variant={s.badge} className="gap-1 px-2.5 py-1 text-xs">
            <Icon className="size-3" />
            {signal.signal}
          </Badge>
          <span className="font-mono text-xs text-slate-500">
            ${signal.price.toFixed(2)}
          </span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
          <div className="rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Exp. 5D Return
            </div>
            <div
              className={cn(
                "mt-0.5 font-mono font-medium data",
                signal.expectedReturn5d >= 0 ? "text-bull-soft" : "text-bear-soft"
              )}
            >
              {formatSignedPct(signal.expectedReturn5d)}
            </div>
          </div>
          <div className="rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              Risk
            </div>
            <div className={cn("mt-0.5 font-medium", RISK_TONE[signal.risk])}>
              {signal.risk}
            </div>
          </div>
        </div>

        {/* Drivers — expand on hover */}
        <div className="mt-4">
          <div className="text-[10px] uppercase tracking-wider text-slate-500">
            Top feature drivers
          </div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {signal.drivers.slice(0, 3).map((d) => (
              <span
                key={d}
                className="rounded-md border border-white/8 bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] text-slate-300"
              >
                {d}
              </span>
            ))}
            {signal.drivers.length > 3 && (
              <span className="rounded-md border border-white/8 bg-white/[0.03] px-2 py-0.5 font-mono text-[10px] text-slate-500">
                +{signal.drivers.length - 3}
              </span>
            )}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between border-t border-white/6 pt-4">
          <span className="font-mono text-[10px] text-slate-500">
            {signal.model}
          </span>
          <Link
            href={`/research?ticker=${signal.ticker}`}
            className="inline-flex items-center gap-1.5 rounded-lg border border-brand-400/25 bg-brand-500/8 px-2.5 py-1.5 text-xs font-medium text-brand-200 transition-all hover:border-brand-400/50 hover:bg-brand-500/15"
          >
            <Sparkles className="size-3" />
            Explain with Research AI
          </Link>
        </div>
      </GlassPanel>
    </motion.div>
  );
}
