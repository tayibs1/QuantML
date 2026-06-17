"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { FlaskConical, GitCommitHorizontal, Plus } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ModelRegistryCard } from "@/components/model-registry-card";
import { FeatureImportanceChart } from "@/components/charts/feature-importance-chart";
import { api } from "@/lib/api";
import {
  models as mockModels,
  featureImportance as mockFeatureImportance,
  modelRegistry as mockRegistry,
  type ModelRecord,
  type ModelVersion,
} from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type FeatureImportance = { feature: string; importance: number };

type Experiment = {
  id: string;
  model: string;
  metric: string;
  status: string;
  time: string;
  tags?: string[];
};

// fallback only; the live feed comes from the trial registry via /api/models
const DEFAULT_EXPERIMENTS: Experiment[] = [
  { id: "exp-2041", model: "backtest", metric: "Sharpe 0.68", status: "finished", time: "2026-06-09" },
  { id: "exp-2033", model: "tuning", metric: "Sharpe 1.09", status: "finished", time: "2026-06-09", tags: ["optuna"] },
  { id: "exp-1987", model: "backtest", metric: "Sharpe 0.61", status: "finished", time: "2026-06-08" },
];

export default function ModelsPage() {
  const [models, setModels] = useState<ModelRecord[]>(mockModels);
  const [featureImportance, setFeatureImportance] =
    useState<FeatureImportance[]>(mockFeatureImportance);
  const [experiments, setExperiments] = useState<Experiment[]>(DEFAULT_EXPERIMENTS);
  const [registry, setRegistry] = useState<ModelVersion[]>(mockRegistry.versions);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .models()
      .then((d) => {
        if (!active || !d) return;
        if (Array.isArray(d.models) && d.models.length) {
          setModels(d.models as ModelRecord[]);
          setLive(true);
        }
        if (Array.isArray(d.featureImportance) && d.featureImportance.length) {
          setFeatureImportance(d.featureImportance as FeatureImportance[]);
        }
        if (Array.isArray(d.experiments) && d.experiments.length) {
          setExperiments(d.experiments as Experiment[]);
        }
        if (d.registry && Array.isArray(d.registry.versions) && d.registry.versions.length) {
          setRegistry(d.registry.versions as ModelVersion[]);
        }
      })
      .catch(() => {
        /* keep mock fallback */
      });
    return () => {
      active = false;
    };
  }, []);

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Model Registry"
        title="Models & Experiments"
        description="Versioned models, walk-forward metrics, feature attribution and experiment tracking."
        actions={
          <>
            <Badge variant={live ? "bull" : "outline"} className="hidden sm:inline-flex">
              <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
              {live ? "Live registry" : "Sample data"}
            </Badge>
            <Button variant="secondary" size="sm">
              <FlaskConical className="size-4" /> Experiments
            </Button>
            <Button size="sm">
              <Plus className="size-4" /> New Run
            </Button>
          </>
        }
      />

      {/* Registry cards */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {models.map((m, i) => (
          <ModelRegistryCard key={m.id} model={m} index={i} />
        ))}
      </div>

      {/* Comparison + feature importance */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <GlassPanel strong className="xl:col-span-2">
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Model Comparison</h3>
            <p className="text-[11px] text-slate-500">
              Out-of-sample, walk-forward validated
            </p>
          </div>
          <div className="overflow-x-auto p-2 no-scrollbar sm:p-3">
            <table className="w-full min-w-[640px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/8 text-left">
                  {["Model", "Status", "Sharpe", "CAGR", "Max DD", "AUC", "Acc.", "Drift"].map(
                    (h) => (
                      <th
                        key={h}
                        className="px-3 py-2.5 font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500"
                      >
                        {h}
                      </th>
                    )
                  )}
                </tr>
              </thead>
              <tbody>
                {models.map((m, i) => (
                  <motion.tr
                    key={m.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className={cn(
                      "border-b border-white/5 transition-colors hover:bg-white/[0.02]",
                      m.status === "Production candidate" && "bg-brand-500/[0.04]"
                    )}
                  >
                    <td className="px-3 py-3">
                      <div className="font-medium text-white">{m.name}</div>
                      <div className="font-mono text-[10px] text-slate-500">
                        {m.family}
                      </div>
                    </td>
                    <td className="px-3 py-3">
                      <Badge
                        variant={
                          m.status === "Production candidate"
                            ? "brand"
                            : m.status === "Champion"
                              ? "bull"
                              : m.status === "Experimental"
                                ? "violet"
                                : "default"
                        }
                      >
                        {m.status}
                      </Badge>
                    </td>
                    <td className="px-3 py-3 font-mono text-xs font-medium text-brand-200 data">
                      {m.sharpe.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-bull-soft data">
                      {m.cagr.toFixed(1)}%
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-bear-soft data">
                      {m.maxDrawdown.toFixed(1)}%
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-300 data">
                      {m.auc.toFixed(2)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-300 data">
                      {(m.accuracy * 100).toFixed(1)}%
                    </td>
                    <td className="px-3 py-3">
                      <span
                        className={cn(
                          "font-mono text-xs",
                          m.drift === "Low"
                            ? "text-bull-soft"
                            : m.drift === "Medium"
                              ? "text-hold-soft"
                              : "text-bear-soft"
                        )}
                      >
                        {m.drift}
                      </span>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassPanel>

        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Feature Importance</h3>
            <p className="text-[11px] text-slate-500">XGBoost-v3 · mean |SHAP|</p>
          </div>
          <div className="p-4">
            <FeatureImportanceChart height={340} data={featureImportance} />
          </div>
        </GlassPanel>
      </div>

      {/* Model registry — versioned champions, DSR-gated promotions */}
      <GlassPanel strong>
        <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
          <h3 className="text-sm font-semibold text-white">Model Registry</h3>
          <span className="font-mono text-[10px] text-slate-500">
            promotion gate · Deflated Sharpe ≥ 0.90
          </span>
        </div>
        <div className="overflow-x-auto p-2 no-scrollbar sm:p-3">
          <table className="w-full min-w-[640px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-white/8 text-left">
                {["Version", "Status", "Sharpe", "AUC", "DSR gate", "Promoted"].map((h) => (
                  <th
                    key={h}
                    className="px-3 py-2.5 font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {registry.map((v, i) => (
                <motion.tr
                  key={v.id}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.04 }}
                  className={cn(
                    "border-b border-white/5 transition-colors hover:bg-white/[0.02]",
                    v.status === "champion" && "bg-bull/[0.05]"
                  )}
                >
                  <td className="px-3 py-3">
                    <span className="font-medium text-white">{v.version}</span>
                    <span className="ml-2 font-mono text-[10px] text-slate-500">{v.name}</span>
                  </td>
                  <td className="px-3 py-3">
                    <Badge variant={v.status === "champion" ? "bull" : "default"}>
                      {v.status}
                    </Badge>
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-brand-200 data">
                    {v.metrics.sharpe?.toFixed(2) ?? "—"}
                  </td>
                  <td className="px-3 py-3 font-mono text-xs text-slate-300 data">
                    {v.metrics.auc?.toFixed(3) ?? "—"}
                  </td>
                  <td className="px-3 py-3">
                    <span
                      className={cn(
                        "font-mono text-xs",
                        v.gatePassed ? "text-bull-soft" : "text-bear-soft"
                      )}
                    >
                      {v.dsr ?? "—"} {v.gatePassed ? "✓" : "✗"}
                    </span>
                  </td>
                  <td className="px-3 py-3 font-mono text-[10px] text-slate-500">
                    {v.promotedAt ?? "—"}
                  </td>
                </motion.tr>
              ))}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Experiment tracking */}
      <GlassPanel strong>
        <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <GitCommitHorizontal className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">Experiment Tracking</h3>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            MLflow-compatible
          </span>
        </div>
        <div className="divide-y divide-white/5">
          {experiments.map((e, i) => (
            <motion.div
              key={e.id}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-4 px-5 py-3 transition-colors hover:bg-white/[0.02]"
            >
              <span
                className={cn(
                  "size-2 shrink-0 rounded-full",
                  e.status === "running" ? "animate-pulse bg-hold" : "bg-bull"
                )}
              />
              <span className="w-24 shrink-0 font-mono text-xs text-slate-400">
                {e.id}
              </span>
              <span className="flex-1 text-sm font-medium text-slate-200">
                {e.model}
              </span>
              <span className="hidden font-mono text-xs text-brand-200 sm:block">
                {e.metric}
              </span>
              <Badge variant={e.status === "running" ? "hold" : "default"}>
                {e.status}
              </Badge>
              <span className="w-16 shrink-0 text-right font-mono text-[10px] text-slate-500">
                {e.time}
              </span>
            </motion.div>
          ))}
        </div>
      </GlassPanel>
    </PageTransition>
  );
}
