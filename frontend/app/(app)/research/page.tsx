"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Bot, Database, FileText, Newspaper, ShieldCheck, Sparkles } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { ResearchAssistant } from "@/components/research-assistant";
import { examplePrompts } from "@/lib/mock-data";

const SOURCES = [
  { icon: FileText, label: "SEC filings", count: "10-K / 10-Q · 12.4k docs" },
  { icon: Newspaper, label: "Market news", count: "Reuters · 48k articles" },
  { icon: Database, label: "Model reports", count: "SHAP · drift · backtests" },
  { icon: Sparkles, label: "Earnings", count: "Transcripts · 6.2k calls" },
];

function ResearchInner() {
  const params = useSearchParams();
  const ticker = params.get("ticker");
  const initialPrompt = ticker
    ? `Why did the model generate its current signal for ${ticker}?`
    : undefined;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      {/* Assistant */}
      <div className="lg:col-span-2">
        <ResearchAssistant initialPrompt={initialPrompt} />
      </div>

      {/* Context rail */}
      <div className="space-y-6">
        <GlassPanel strong inset>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">How it works</h3>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            The assistant retrieves relevant filings, news, earnings and model
            reports, then grounds its explanation in those sources alongside the
            live model signal. It{" "}
            <span className="text-slate-200">explains and contextualises</span> —
            it does not place trades or give financial advice.
          </p>
        </GlassPanel>

        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Knowledge base</h3>
            <p className="text-[11px] text-slate-500">Indexed retrieval corpus</p>
          </div>
          <div className="space-y-2 p-4">
            {SOURCES.map((s) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.label}
                  className="flex items-center gap-3 rounded-xl border border-white/6 bg-white/[0.02] p-3"
                >
                  <span className="grid size-9 place-items-center rounded-lg border border-white/8 bg-white/[0.03]">
                    <Icon className="size-4 text-slate-300" />
                  </span>
                  <div>
                    <div className="text-sm font-medium text-slate-200">
                      {s.label}
                    </div>
                    <div className="font-mono text-[10px] text-slate-500">
                      {s.count}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </GlassPanel>

        <GlassPanel strong inset>
          <div className="flex items-center gap-2">
            <Bot className="size-4 text-violet-glow" />
            <h3 className="text-sm font-semibold text-white">Try asking</h3>
          </div>
          <ul className="mt-3 space-y-2">
            {examplePrompts.map((p) => (
              <li
                key={p}
                className="rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2 text-xs text-slate-400"
              >
                {p}
              </li>
            ))}
          </ul>
        </GlassPanel>
      </div>
    </div>
  );
}

export default function ResearchPage() {
  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="RAG Market Intelligence"
        title="Research AI"
        description="Ask why a signal fired, what risks contradict it, and how similar setups performed — every answer grounded in retrieved sources."
        actions={<Badge variant="violet">Retrieval-augmented</Badge>}
      />
      <Suspense fallback={<div className="h-96 animate-pulse rounded-2xl glass" />}>
        <ResearchInner />
      </Suspense>
    </PageTransition>
  );
}
