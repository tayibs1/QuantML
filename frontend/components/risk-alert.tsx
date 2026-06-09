"use client";

import { motion } from "motion/react";
import { AlertTriangle, Info, ShieldAlert } from "lucide-react";
import type { RiskFlag } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const LEVEL = {
  info: {
    Icon: Info,
    border: "border-brand-400/25",
    bg: "bg-brand-500/[0.06]",
    icon: "text-brand-300",
    dot: "bg-brand-400",
    label: "INFO",
  },
  warning: {
    Icon: AlertTriangle,
    border: "border-hold/30",
    bg: "bg-hold/[0.06]",
    icon: "text-hold-soft",
    dot: "bg-hold",
    label: "WARNING",
  },
  critical: {
    Icon: ShieldAlert,
    border: "border-bear/35",
    bg: "bg-bear/[0.07]",
    icon: "text-bear-soft",
    dot: "bg-bear",
    label: "CRITICAL",
  },
};

export function RiskAlert({ flag, index = 0 }: { flag: RiskFlag; index?: number }) {
  const cfg = LEVEL[flag.level];
  const Icon = cfg.Icon;

  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay: index * 0.06 }}
      className={cn(
        "relative overflow-hidden rounded-xl border p-3.5",
        cfg.border,
        cfg.bg
      )}
    >
      {flag.level === "critical" && (
        <span className="absolute right-3 top-3 flex size-2">
          <span className="absolute inline-flex size-full animate-ping rounded-full bg-bear/60" />
          <span className={cn("relative inline-flex size-2 rounded-full", cfg.dot)} />
        </span>
      )}
      <div className="flex gap-3">
        <div className={cn("mt-0.5 shrink-0", cfg.icon)}>
          <Icon className="size-4" />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "font-mono text-[9px] font-semibold tracking-widest",
                cfg.icon
              )}
            >
              {cfg.label}
            </span>
            {flag.metric && (
              <span className="font-mono text-[10px] text-slate-500">
                {flag.metric}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm font-medium text-slate-100">{flag.title}</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-400">
            {flag.detail}
          </p>
        </div>
      </div>
    </motion.div>
  );
}
