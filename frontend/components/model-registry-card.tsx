"use client";

import { motion } from "motion/react";
import { CircuitBoard, GitBranch, Calendar } from "lucide-react";
import { GlassPanel } from "./glass-panel";
import { Badge } from "./ui/badge";
import type { ModelRecord } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

const STATUS_VARIANT: Record<ModelRecord["status"], "brand" | "violet" | "hold" | "default" | "bull"> = {
  "Production candidate": "brand",
  Champion: "bull",
  Experimental: "violet",
  Baseline: "default",
  Archived: "default",
};

const DRIFT_TONE: Record<ModelRecord["drift"], string> = {
  Low: "text-bull-soft",
  Medium: "text-hold-soft",
  High: "text-bear-soft",
};

function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <div className={cn("mt-0.5 font-mono text-sm font-medium data", tone ?? "text-slate-100")}>
        {value}
      </div>
    </div>
  );
}

export function ModelRegistryCard({
  model,
  index = 0,
}: {
  model: ModelRecord;
  index?: number;
}) {
  const isCandidate = model.status === "Production candidate";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay: index * 0.05 }}
      whileHover={{ y: -4 }}
    >
      <GlassPanel
        strong
        glow
        className={cn(
          "h-full p-5",
          isCandidate && "ring-1 ring-brand-400/25"
        )}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl border border-white/8 bg-white/[0.03]">
              <CircuitBoard className="size-5 text-brand-300" />
            </span>
            <div>
              <h3 className="font-semibold text-white">{model.name}</h3>
              <p className="text-xs text-slate-500">{model.family}</p>
            </div>
          </div>
          <Badge variant={STATUS_VARIANT[model.status]}>{model.status}</Badge>
        </div>

        <div className="mt-5 grid grid-cols-3 gap-4">
          <Stat label="Sharpe" value={model.sharpe.toFixed(2)} tone="text-brand-200" />
          <Stat
            label="Max DD"
            value={`${model.maxDrawdown.toFixed(1)}%`}
            tone="text-bear-soft"
          />
          <Stat
            label="Drift"
            value={model.drift}
            tone={DRIFT_TONE[model.drift]}
          />
        </div>

        <div className="mt-4 grid grid-cols-3 gap-4 border-t border-white/6 pt-4">
          <Stat label="CAGR" value={`${model.cagr.toFixed(1)}%`} tone="text-bull-soft" />
          <Stat label="AUC" value={model.auc.toFixed(2)} />
          <Stat label="Features" value={`${model.features}`} />
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-white/6 pt-4 font-mono text-[10px] text-slate-500">
          <span className="inline-flex items-center gap-1">
            <GitBranch className="size-3" /> {model.validation}
          </span>
          <span className="inline-flex items-center gap-1">
            <Calendar className="size-3" /> {model.trainingWindow}
          </span>
          <span className="ml-auto rounded bg-white/[0.04] px-1.5 py-0.5">
            {model.experimentId}
          </span>
        </div>
      </GlassPanel>
    </motion.div>
  );
}
