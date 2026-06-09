"use client";

import { motion } from "motion/react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { GlassPanel } from "./glass-panel";
import { AnimatedCounter } from "./animated-counter";
import { Sparkline } from "./charts/sparkline";
import { sparkline } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

export interface MetricCardProps {
  label: string;
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  delta?: number;
  /** Which direction is "good". Drawdown/exposure flip this. */
  positiveIsGood?: boolean;
  sparkSeed?: number;
  sparkUp?: boolean;
  index?: number;
}

export function MetricCard({
  label,
  value,
  decimals = 0,
  prefix = "",
  suffix = "",
  delta,
  positiveIsGood = true,
  sparkSeed = 1,
  sparkUp = true,
  index = 0,
}: MetricCardProps) {
  const good = delta == null ? true : positiveIsGood ? delta >= 0 : delta <= 0;
  const tone = good ? "bull" : "bear";
  const accent = good ? "#34d399" : "#fb7185";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.05, ease: [0.21, 0.6, 0.35, 1] }}
      whileHover={{ y: -4 }}
    >
      <GlassPanel glow inset className="group h-full">
        <div className="flex items-start justify-between gap-3">
          <span className="text-xs font-medium text-slate-400">{label}</span>
          {delta != null && (
            <span
              className={cn(
                "inline-flex items-center gap-0.5 rounded-md px-1.5 py-0.5 font-mono text-[11px] font-medium",
                tone === "bull"
                  ? "bg-bull/10 text-bull-soft"
                  : "bg-bear/10 text-bear-soft"
              )}
            >
              {good ? (
                <ArrowUpRight className="size-3" />
              ) : (
                <ArrowDownRight className="size-3" />
              )}
              {Math.abs(delta).toFixed(decimals === 0 ? 1 : decimals)}
              {suffix === "%" ? "%" : ""}
            </span>
          )}
        </div>

        <div className="mt-3 flex items-end justify-between gap-3">
          <div className="text-2xl font-semibold tracking-tight text-white data sm:text-[28px]">
            <AnimatedCounter
              value={value}
              decimals={decimals}
              prefix={prefix}
              suffix={suffix}
            />
          </div>
        </div>

        <div className="-mb-1 mt-2 h-10 opacity-80 transition-opacity group-hover:opacity-100">
          <Sparkline
            id={`m-${sparkSeed}`}
            data={sparkline(sparkSeed * 13 + 3, 24, sparkUp)}
            color={accent}
          />
        </div>
      </GlassPanel>
    </motion.div>
  );
}
