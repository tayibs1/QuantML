"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Activity, GitCompareArrows } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Sparkline } from "@/components/charts/sparkline";
import { api, type ValidationStudies } from "@/lib/api";
import { cn } from "@/lib/utils";

// Sample fallback — the same shape the backend serves; replaced by live data when present.
const MOCK: ValidationStudies = {
  rollingWindow: {
    note: "Anchored weekly walk-forward (refit each week on prior data only).",
    generatedAt: "2026-06-16",
    baseline: { sharpe: 1.19, auc: 0.54, accuracy: 0.366 },
    rolling: { sharpe: 1.15, auc: 0.5327, accuracy: 0.3648, hitRate: 0.5882, weeks: 323 },
    weekly: Array.from({ length: 24 }, (_, i) => ({
      date: `w${i}`,
      basketReturn: 0.003 + Math.sin(i / 3) * 0.004,
      accuracy: 0.37,
      nBuy: 12,
    })),
  },
  windowComparison: {
    note: "Capped look-backs, aligned to the same evaluation weeks.",
    generatedAt: "2026-06-16",
    step: 10,
    windows: {
      "2y": { sharpe: 1.46, volatility: 0.2509, hitRate: 0.6066, maxDrawdown: -0.2203 },
      "3y": { sharpe: 1.75, volatility: 0.2376, hitRate: 0.6721, maxDrawdown: -0.2396 },
      "4y": { sharpe: 1.9, volatility: 0.2426, hitRate: 0.623, maxDrawdown: -0.2209 },
      "5y": { sharpe: 1.66, volatility: 0.2499, hitRate: 0.6393, maxDrawdown: -0.2111 },
      expanding: { sharpe: 1.77, volatility: 0.2433, hitRate: 0.6721, maxDrawdown: -0.1952 },
    },
    bestBySharpe: "4y",
    steadiestByVol: "3y",
  },
  regimeModels: {
    general: { sharpe: 1.19, auc: 0.54 },
    ensemble: { sharpe: 0.95, auc: 0.537 },
    year2022: { general: -0.77, ensemble: -0.5 },
    ensembleBeatsGeneral: false,
    verdict:
      "No overall improvement; general model stays champion. It softened the 2022 bear drawdown but the thin bear sample makes the specialist too noisy to ship.",
  },
  ood: {
    trainEnd: "2023-01-01",
    trainRows: 55342,
    testRows: 47872,
    metrics: { sharpe: 1.89, auc: 0.54, accuracy: 0.366 },
    overallDrift: "OK",
    eraDrift: [],
  },
  confidence: {
    sizing: {
      equalWeight: { sharpe: 1.19, maxDrawdown: -0.293 },
      confidenceWeighted: { sharpe: 1.21, maxDrawdown: -0.2969 },
    },
    confidenceImprovesSharpe: true,
    calibration: { brier: 0.227, ece: 0.0432, bins: [] },
  },
  onlineLearning: {
    cadences: {
      weekly: { refitEvery: 1, refits: 76, seconds: 745.9, sharpe: 1.5, hitRate: 0.61, weeks: 76 },
      biweekly: { refitEvery: 2, refits: 38, seconds: 323.4, sharpe: 1.67, hitRate: 0.63, weeks: 76 },
      monthly: { refitEvery: 4, refits: 19, seconds: 152.7, sharpe: 1.63, hitRate: 0.62, weeks: 76 },
      quarterly: { refitEvery: 12, refits: 7, seconds: 59.2, sharpe: 1.44, hitRate: 0.59, weeks: 76 },
    },
    fullRetrainSharpe: 1.5,
  },
};

const WINDOW_ORDER = ["2y", "3y", "4y", "5y", "expanding"];

function pct(x: number | undefined, dp = 1) {
  return `${((x ?? 0) * 100).toFixed(dp)}%`;
}

export default function ValidationPage() {
  const [data, setData] = useState<ValidationStudies>(MOCK);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .validation()
      .then((d) => {
        if (!active || !d) return;
        // only swap in live data once the studies have actually run
        if (d.rollingWindow || d.windowComparison) {
          setData({
            rollingWindow: d.rollingWindow ?? MOCK.rollingWindow,
            windowComparison: d.windowComparison ?? MOCK.windowComparison,
            regimeModels: d.regimeModels ?? MOCK.regimeModels,
            ood: d.ood ?? MOCK.ood,
            confidence: d.confidence ?? MOCK.confidence,
            onlineLearning: d.onlineLearning ?? MOCK.onlineLearning,
          });
          setLive(Boolean(d.rollingWindow));
        }
      })
      .catch(() => {
        /* keep sample fallback */
      });
    return () => {
      active = false;
    };
  }, []);

  const rw = data.rollingWindow ?? MOCK.rollingWindow!;
  const wc = data.windowComparison ?? MOCK.windowComparison!;
  const reg = data.regimeModels ?? MOCK.regimeModels!;
  const ood = data.ood ?? MOCK.ood!;
  const conf = data.confidence ?? MOCK.confidence!;
  const online = data.onlineLearning ?? MOCK.onlineLearning!;
  const cadenceOrder = ["weekly", "biweekly", "monthly", "quarterly"];
  const bestCadence = Object.entries(online.cadences).sort(
    (a, b) => b[1].sharpe - a[1].sharpe
  )[0]?.[0];

  // cumulative equity of the weekly BUY basket, for the sparkline
  let acc = 1;
  const curve = rw.weekly.map((w) => {
    acc *= 1 + (w.basketReturn ?? 0);
    return { v: acc };
  });

  const tiles = [
    { k: "Sharpe", base: rw.baseline.sharpe, roll: rw.rolling.sharpe, dp: 2 },
    { k: "AUC", base: rw.baseline.auc, roll: rw.rolling.auc, dp: 3 },
    { k: "Accuracy", base: rw.baseline.accuracy, roll: rw.rolling.accuracy, dp: 3, isPct: true },
  ];

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Validation"
        title="Robustness & Realism"
        description="Stress-testing the model the way live trading runs: weekly refits, training-window sensitivity, and leakage-safe out-of-sample scoring."
        actions={
          <Badge variant={live ? "bull" : "outline"} className="hidden sm:inline-flex">
            <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
            {live ? "Live studies" : "Sample data"}
          </Badge>
        }
      />

      {/* Rolling-window vs 6-fold baseline */}
      <GlassPanel strong>
        <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
          <Activity className="size-4 text-brand-300" />
          <div>
            <h3 className="text-sm font-semibold text-white">Live-cadence validation</h3>
            <p className="text-[11px] text-slate-500">
              Anchored weekly walk-forward vs the 6-fold baseline · {rw.rolling.weeks ?? 0} weeks
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-5 p-5 lg:grid-cols-3">
          <div className="space-y-3 lg:col-span-1">
            {tiles.map((t) => (
              <div
                key={t.k}
                className="flex items-center justify-between rounded-lg border border-white/6 bg-white/[0.02] px-4 py-3"
              >
                <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
                  {t.k}
                </span>
                <span className="flex items-baseline gap-2 font-mono text-sm">
                  <span className="text-slate-500">
                    {t.isPct ? pct(t.base, t.dp) : (t.base ?? 0).toFixed(t.dp)}
                  </span>
                  <span className="text-slate-600">→</span>
                  <span className="font-medium text-brand-200">
                    {t.isPct ? pct(t.roll, t.dp) : (t.roll ?? 0).toFixed(t.dp)}
                  </span>
                </span>
              </div>
            ))}
          </div>

          <div className="lg:col-span-2">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-slate-400">Weekly BUY-basket equity (out-of-sample)</span>
              <span className="font-mono text-[10px] text-slate-500">
                hit rate {pct(rw.rolling.hitRate, 0)}
              </span>
            </div>
            <Sparkline data={curve} id="rolling-equity" height={120} />
            <p className="mt-3 text-[11px] leading-relaxed text-slate-500">
              {rw.note} The baseline reports one number for the whole period; the rolling
              scheme refits every week on prior data only, which is closer to how a live
              book operates — and the gap between the two is the honest cost of realism.
            </p>
          </div>
        </div>
      </GlassPanel>

      {/* Training-window sensitivity */}
      <GlassPanel strong>
        <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
          <div className="flex items-center gap-2">
            <GitCompareArrows className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">Training-window sensitivity</h3>
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            best Sharpe: {wc.bestBySharpe ?? "—"} · steadiest: {wc.steadiestByVol ?? "—"}
          </span>
        </div>
        <div className="overflow-x-auto p-2 no-scrollbar sm:p-3">
          <table className="w-full min-w-[560px] border-collapse text-sm">
            <thead>
              <tr className="border-b border-white/8 text-left">
                {["Look-back", "Sharpe", "Volatility", "Hit rate", "Max DD"].map((h) => (
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
              {WINDOW_ORDER.filter((w) => wc.windows[w]).map((name, i) => {
                const m = wc.windows[name];
                const best = name === wc.bestBySharpe;
                return (
                  <motion.tr
                    key={name}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.04 }}
                    className={cn(
                      "border-b border-white/5 transition-colors hover:bg-white/[0.02]",
                      best && "bg-brand-500/[0.05]"
                    )}
                  >
                    <td className="px-3 py-3 font-medium text-white">
                      {name}
                      {best && (
                        <Badge variant="bull" className="ml-2">
                          best
                        </Badge>
                      )}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs font-medium text-brand-200 data">
                      {(m.sharpe ?? 0).toFixed(2)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-300 data">
                      {pct(m.volatility)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-slate-300 data">
                      {pct(m.hitRate, 0)}
                    </td>
                    <td className="px-3 py-3 font-mono text-xs text-bear-soft data">
                      {pct(m.maxDrawdown)}
                    </td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </GlassPanel>

      {/* Regime specialisation + out-of-distribution robustness */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Regime specialisation</h3>
            <p className="text-[11px] text-slate-500">Bull/bear specialists vs one general model</p>
          </div>
          <div className="space-y-3 p-5">
            <div className="grid grid-cols-3 gap-2 text-center">
              {[
                { k: "General", v: reg.general.sharpe, hl: true },
                { k: "Ensemble", v: reg.ensemble.sharpe, hl: false },
                { k: "2022 (gen→ens)", v: null, txt: `${reg.year2022.general} → ${reg.year2022.ensemble}` },
              ].map((c) => (
                <div key={c.k} className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">{c.k}</div>
                  <div className={cn("mt-1 font-mono text-sm font-medium", c.hl ? "text-brand-200" : "text-slate-200")}>
                    {c.txt ?? (c.v ?? 0).toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500">{reg.verdict}</p>
            <Badge variant={reg.ensembleBeatsGeneral ? "bull" : "default"}>
              {reg.ensembleBeatsGeneral ? "ensemble wins" : "general stays champion"}
            </Badge>
          </div>
        </GlassPanel>

        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Out-of-distribution</h3>
            <p className="text-[11px] text-slate-500">
              Train &lt; {ood.trainEnd}, frozen, evaluated on {ood.testRows.toLocaleString()} unseen rows
            </p>
          </div>
          <div className="space-y-3 p-5">
            <div className="grid grid-cols-3 gap-2 text-center">
              <div className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Sharpe</div>
                <div className="mt-1 font-mono text-sm font-medium text-brand-200">
                  {(ood.metrics.sharpe ?? 0).toFixed(2)}
                </div>
              </div>
              <div className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">AUC</div>
                <div className="mt-1 font-mono text-sm font-medium text-slate-200">
                  {(ood.metrics.auc ?? 0).toFixed(3)}
                </div>
              </div>
              <div className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Era drift</div>
                <div
                  className={cn(
                    "mt-1 font-mono text-sm font-medium",
                    ood.overallDrift === "OK" ? "text-bull-soft" : "text-hold-soft"
                  )}
                >
                  {ood.overallDrift}
                </div>
              </div>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500">
              The frozen pre-2023 model holds its edge on the unseen 2023+ era (AUC matches
              in-sample) and the low feature drift (PSI) confirms cross-sectional normalisation
              kept it in-distribution. The high Sharpe also reflects a favourable bull regime.
            </p>
          </div>
        </GlassPanel>
      </div>

      {/* Confidence sizing + retrain cadence */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GlassPanel strong>
          <div className="border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Conviction sizing & calibration</h3>
            <p className="text-[11px] text-slate-500">Size BUYs by p_buy, and check the probabilities are honest</p>
          </div>
          <div className="space-y-3 p-5">
            <div className="grid grid-cols-2 gap-2 text-center">
              <div className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Equal-weight</div>
                <div className="mt-1 font-mono text-sm text-slate-200">
                  {(conf.sizing.equalWeight.sharpe ?? 0).toFixed(2)}
                </div>
              </div>
              <div className="rounded-lg border border-white/6 bg-white/[0.02] px-2 py-3">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Conviction-weighted</div>
                <div className="mt-1 font-mono text-sm font-medium text-brand-200">
                  {(conf.sizing.confidenceWeighted.sharpe ?? 0).toFixed(2)}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-white/6 bg-white/[0.02] px-4 py-2.5 text-xs">
              <span className="text-slate-400">Calibration</span>
              <span className="font-mono text-slate-300">
                Brier {conf.calibration.brier.toFixed(3)} · ECE {pct(conf.calibration.ece, 1)}
              </span>
            </div>
            <p className="text-[11px] leading-relaxed text-slate-500">
              Sizing by conviction edges equal-weighting, and the low ECE means a 60% call really
              does land ~60% of the time — the probabilities are honest enough to size by.
            </p>
          </div>
        </GlassPanel>

        <GlassPanel strong>
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">Retrain cadence</h3>
            <span className="font-mono text-[10px] text-slate-500">predict weekly · vary refit freq</span>
          </div>
          <div className="overflow-x-auto p-2 no-scrollbar sm:p-3">
            <table className="w-full min-w-[420px] border-collapse text-sm">
              <thead>
                <tr className="border-b border-white/8 text-left">
                  {["Cadence", "Refits", "Sharpe", "Compute"].map((h) => (
                    <th key={h} className="px-3 py-2.5 font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cadenceOrder.filter((c) => online.cadences[c]).map((name) => {
                  const m = online.cadences[name];
                  const best = name === bestCadence;
                  return (
                    <tr key={name} className={cn("border-b border-white/5", best && "bg-brand-500/[0.05]")}>
                      <td className="px-3 py-2.5 font-medium text-white">
                        {name}
                        {best && <Badge variant="bull" className="ml-2">best</Badge>}
                      </td>
                      <td className="px-3 py-2.5 font-mono text-xs text-slate-300 data">{m.refits}</td>
                      <td className="px-3 py-2.5 font-mono text-xs font-medium text-brand-200 data">{m.sharpe.toFixed(2)}</td>
                      <td className="px-3 py-2.5 font-mono text-xs text-slate-400 data">{m.seconds.toFixed(0)}s</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="px-3 py-2 text-[11px] leading-relaxed text-slate-500">
              More frequent isn&apos;t better: monthly refits keep the edge at ~5× less compute than
              weekly, which mildly overfits recent noise. Only quarterly starts to lag.
            </p>
          </div>
        </GlassPanel>
      </div>
    </PageTransition>
  );
}
