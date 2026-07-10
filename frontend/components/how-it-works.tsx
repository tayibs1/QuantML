"use client";

import { useState } from "react";
import { ChevronDown, type LucideIcon } from "lucide-react";
import { motion, AnimatePresence } from "motion/react";
import { GlassPanel } from "@/components/glass-panel";
import { cn } from "@/lib/utils";

export interface HowItWorksStep {
  icon: LucideIcon;
  title: string;
  desc: string;
}

/**
 * A compact, recruiter-friendly pipeline explainer: numbered steps connected
 * left-to-right, each with an icon, a title, and one plain-English line. Reads
 * instantly on a screen recording; collapsible so it never gets in the way.
 */
export function HowItWorks({
  steps,
  title = "How it works",
  defaultOpen = true,
}: {
  steps: HowItWorksStep[];
  title?: string;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <GlassPanel className="overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-3 text-left transition-colors hover:bg-white/[0.02]"
      >
        <div className="flex items-center gap-2">
          <span className="flex size-5 items-center justify-center rounded-md bg-brand-400/15 font-mono text-[10px] font-bold text-brand-300">
            ?
          </span>
          <span className="text-sm font-semibold text-white">{title}</span>
          <span className="hidden font-mono text-[10px] uppercase tracking-wider text-slate-500 sm:inline">
            · the pipeline behind every call
          </span>
        </div>
        <ChevronDown className={cn("size-4 text-slate-500 transition-transform", open && "rotate-180")} />
      </button>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
          >
            <div className="grid grid-cols-1 gap-px border-t border-white/6 bg-white/[0.02] sm:grid-cols-2 lg:grid-cols-4">
              {steps.map((s, i) => {
                const Icon = s.icon;
                return (
                  <div key={s.title} className="relative bg-ink-900/40 p-4">
                    <div className="mb-2 flex items-center gap-2">
                      <span className="flex size-6 items-center justify-center rounded-lg border border-brand-400/25 bg-brand-400/10 font-mono text-[11px] font-bold text-brand-300">
                        {i + 1}
                      </span>
                      <Icon className="size-4 text-slate-400" />
                      {/* connector arrow to the next step (desktop only) */}
                      {i < steps.length - 1 && (
                        <span className="pointer-events-none absolute -right-px top-6 hidden text-slate-600 lg:block">
                          →
                        </span>
                      )}
                    </div>
                    <div className="text-sm font-semibold text-white">{s.title}</div>
                    <p className="mt-1 text-[12px] leading-relaxed text-slate-400">{s.desc}</p>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </GlassPanel>
  );
}
