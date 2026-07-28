"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { AlertTriangle, Bot, Database, Layers, ShieldCheck, Wrench } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { ResearchAI } from "@/components/research-ai";
import { api, type ResearchHealth } from "@/lib/api";

/** Readable names for the artifact types the index reports. */
const TYPE_LABELS: Record<string, string> = {
  latest_signal: "Live signals",
  signal_history: "Universe summary",
  shap_summary: "Feature attribution",
  feature_dictionary: "Feature definitions",
  validation_report: "Validation studies",
  walk_forward_report: "Walk-forward studies",
  backtest_report: "Backtest reports",
  risk_report: "Risk framework",
  model_card: "Model cards",
  model_registry_entry: "Model registry",
  drift_report: "Drift reports",
  calibration_report: "Calibration studies",
  documentation: "Project docs",
  research_note: "Research notes",
};

const TOOLS = [
  ["get_latest_signal", "signal, confidence, expected return, risk"],
  ["get_top_shap_drivers", "which features pushed the call, and which way"],
  ["get_model_metrics", "AUC and accuracy against their chance baselines"],
  ["get_backtest_summary", "net-of-cost performance and this name's trades"],
  ["get_risk_summary", "position sizing and the caps that bind it"],
  ["get_feature_definition", "what a feature is and how it's calculated"],
];

/** Counts come from the live index rather than being written in by hand, so the
 *  panel can't drift out of step with what's actually searchable. */
function KnowledgeBase() {
  const [health, setHealth] = useState<ResearchHealth | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    api
      .researchHealth()
      .then(setHealth)
      .catch(() => setFailed(true));
  }, []);

  const entries = Object.entries(health?.index.byType ?? {});

  return (
    <GlassPanel strong>
      <div className="border-b border-white/6 px-5 py-3.5">
        <h3 className="text-sm font-semibold text-white">Indexed corpus</h3>
        <p className="text-[11px] text-slate-500">
          {health
            ? `${health.index.chunks} chunks from ${health.index.artifacts} artifacts`
            : failed
              ? "Backend not reachable"
              : "Loading…"}
        </p>
      </div>

      <div className="space-y-1.5 p-4">
        {failed && (
          <p className="text-[11px] leading-relaxed text-slate-500">
            The FastAPI backend isn&apos;t running, so the assistant falls back to
            snapshot answers without cited artifacts. Start it with{" "}
            <code className="rounded bg-white/5 px-1 font-mono text-[10px]">
              uvicorn main:app --port 8000
            </code>{" "}
            from <span className="font-mono">backend/</span>.
          </p>
        )}

        {entries.map(([type, count]) => (
          <div
            key={type}
            className="flex items-center gap-3 rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2"
          >
            <Layers className="size-3.5 shrink-0 text-slate-500" />
            <span className="truncate text-xs text-slate-300">
              {TYPE_LABELS[type] ?? type}
            </span>
            <span className="ml-auto font-mono text-[10px] text-slate-500">{count}</span>
          </div>
        ))}

        {health && (
          <div className="mt-3 border-t border-white/6 pt-3 font-mono text-[10px] leading-relaxed text-slate-600">
            <div>embedder · {health.embedding.active}</div>
            <div>store · {health.index.backend}</div>
            <div>
              llm · {health.llm.provider}
              {health.llm.mockMode && " (no key needed)"}
            </div>
          </div>
        )}

        <p className="pt-2 text-[11px] leading-relaxed text-slate-500">
          Only QuantML&apos;s own output is indexed. There are no filings, news
          articles or earnings transcripts in this corpus, so the assistant cannot
          answer from them.
        </p>
      </div>
    </GlassPanel>
  );
}

function ResearchInner() {
  const params = useSearchParams();
  const ticker = params.get("ticker");
  const initialPrompt = ticker
    ? `Why did the model give ${ticker} its current signal?`
    : undefined;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="lg:col-span-2">
        <ResearchAI initialPrompt={initialPrompt} />
      </div>

      <div className="space-y-6">
        <GlassPanel strong inset>
          <div className="flex items-center gap-2">
            <ShieldCheck className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">How it works</h3>
          </div>
          <p className="mt-3 text-sm leading-relaxed text-slate-400">
            Two things happen for every question. Exact figures are looked up
            directly from the artifacts, so no number is ever generated. Then the
            explanatory documents are searched to give those numbers meaning.
          </p>
          <p className="mt-2.5 text-sm leading-relaxed text-slate-400">
            The answer is then checked back against that evidence. Figures that
            don&apos;t appear in it get flagged, and so does anything that reads
            like advice.
          </p>
        </GlassPanel>

        <KnowledgeBase />

        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <div className="flex items-center gap-2">
              <Wrench className="size-4 text-brand-300" />
              <h3 className="text-sm font-semibold text-white">Exact lookups</h3>
            </div>
            <p className="text-[11px] text-slate-500">
              Deterministic — the model never invents these
            </p>
          </div>
          <div className="space-y-2 p-4">
            {TOOLS.map(([name, what]) => (
              <div key={name}>
                <div className="font-mono text-[10px] text-brand-200/80">{name}</div>
                <div className="text-[11px] leading-relaxed text-slate-500">{what}</div>
              </div>
            ))}
          </div>
        </GlassPanel>

        <GlassPanel strong inset>
          <div className="flex items-center gap-2">
            <AlertTriangle className="size-4 text-hold-soft" />
            <h3 className="text-sm font-semibold text-white">Limitations</h3>
          </div>
          <ul className="mt-3 space-y-2 text-[11px] leading-relaxed text-slate-400">
            {[
              "Model-generated research, not financial advice. It will not tell you what to do.",
              "It can only answer from indexed QuantML artifacts. It has no fundamentals, news or filings.",
              "Missing evidence is reported rather than guessed at.",
              "It explains what the model produced. It does not judge whether the model is right.",
            ].map((line) => (
              <li key={line} className="flex gap-2">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-slate-600" />
                {line}
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
        eyebrow="Artifact-grounded RAG"
        title="Research AI"
        description="Ask why a signal fired, which features drove it, what the validation evidence supports and what would make it unreliable — every answer cited back to a QuantML artifact."
        actions={
          <span className="flex items-center gap-2">
            <Badge variant="violet">
              <Database className="mr-1 inline size-3" />
              Retrieval + tools
            </Badge>
            <Badge variant="brand">
              <Bot className="mr-1 inline size-3" />
              Cited
            </Badge>
          </span>
        }
      />
      <Suspense fallback={<div className="h-96 animate-pulse rounded-2xl glass" />}>
        <ResearchInner />
      </Suspense>
    </PageTransition>
  );
}
