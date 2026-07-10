"use client";

import { type LucideIcon } from "lucide-react";
import { GlassPanel } from "@/components/glass-panel";

export interface HowItWorksStep {
  icon: LucideIcon;
  title: string;
  desc: string;
}

/**
 * A compact, recruiter-friendly pipeline explainer: numbered steps, each with an
 * icon, a title, and one plain-English line. Reads instantly on a screen
 * recording.
 */
export function HowItWorks({ steps, title = "How it works" }: { steps: HowItWorksStep[]; title?: string }) {
  return (
    <GlassPanel className="overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-3">
        <span className="flex size-5 items-center justify-center rounded-md bg-brand-400/15 font-mono text-[10px] font-bold text-brand-300">
          ?
        </span>
        <span className="text-sm font-semibold text-white">{title}</span>
        <span className="hidden font-mono text-[10px] uppercase tracking-wider text-slate-500 sm:inline">
          · the pipeline behind every call
        </span>
      </div>

      <div className="grid grid-cols-1 gap-px border-t border-white/6 bg-white/[0.02] sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => {
          const Icon = s.icon;
          return (
            <div key={s.title} className="bg-ink-900/40 p-4">
              <div className="mb-2 flex items-center gap-2">
                <span className="flex size-6 items-center justify-center rounded-lg border border-brand-400/25 bg-brand-400/10 font-mono text-[11px] font-bold text-brand-300">
                  {i + 1}
                </span>
                <Icon className="size-4 text-slate-400" />
              </div>
              <div className="text-sm font-semibold text-white">{s.title}</div>
              <p className="mt-1 text-[12px] leading-relaxed text-slate-400">{s.desc}</p>
            </div>
          );
        })}
      </div>
    </GlassPanel>
  );
}
