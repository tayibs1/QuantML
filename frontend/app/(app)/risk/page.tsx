"use client";

import { useEffect, useState } from "react";
import { motion } from "motion/react";
import { Gauge, ListChecks, ShieldAlert } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { RiskAlert } from "@/components/risk-alert";
import { ExposureDonut, exposurePalette } from "@/components/charts/exposure-donut";
import { VolatilityChart } from "@/components/charts/volatility-chart";
import { api } from "@/lib/api";
import {
  exposureByAsset as mockExposureByAsset,
  exposureBySector as mockExposureBySector,
  positionRules as mockPositionRules,
  riskBudget as mockRiskBudget,
  riskFlags as mockRiskFlags,
  volatilityRegime as mockVolatilityRegime,
  type RiskFlag,
} from "@/lib/mock-data";
import { cn } from "@/lib/utils";

function DonutCard({
  title,
  data,
}: {
  title: string;
  data: { name: string; value: number }[];
}) {
  return (
    <GlassPanel strong>
      <div className="border-b border-white/6 px-5 py-3.5">
        <h3 className="text-sm font-semibold text-white">{title}</h3>
      </div>
      <div className="grid grid-cols-2 items-center gap-2 p-4">
        <ExposureDonut data={data} height={200} />
        <ul className="space-y-1.5">
          {data.map((d, i) => (
            <li key={d.name} className="flex items-center gap-2 text-xs">
              <span
                className="size-2.5 rounded-sm"
                style={{ background: exposurePalette[i % exposurePalette.length] }}
              />
              <span className="text-slate-300">{d.name}</span>
              <span className="ml-auto font-mono text-slate-400 data">
                {d.value}%
              </span>
            </li>
          ))}
        </ul>
      </div>
    </GlassPanel>
  );
}

export default function RiskPage() {
  const [exposureByAsset, setExposureByAsset] = useState(mockExposureByAsset);
  const [exposureBySector, setExposureBySector] = useState(mockExposureBySector);
  const [riskBudget, setRiskBudget] = useState(mockRiskBudget);
  const [riskFlags, setRiskFlags] = useState<RiskFlag[]>(mockRiskFlags);
  const [positionRules, setPositionRules] = useState<string[]>(mockPositionRules);
  const [volatilityRegime, setVolatilityRegime] = useState(mockVolatilityRegime);
  const [live, setLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .risk()
      .then((d) => {
        if (!active || !d) return;
        if (Array.isArray(d.exposureByAsset)) setExposureByAsset(d.exposureByAsset);
        if (Array.isArray(d.exposureBySector)) setExposureBySector(d.exposureBySector);
        if (Array.isArray(d.budget)) setRiskBudget(d.budget);
        if (Array.isArray(d.flags)) setRiskFlags(d.flags as RiskFlag[]);
        if (Array.isArray(d.positionRules)) setPositionRules(d.positionRules);
        if (Array.isArray(d.volatilityRegime)) setVolatilityRegime(d.volatilityRegime);
        setLive(true);
      })
      .catch(() => {
        /* keep mock fallback */
      });
    return () => {
      active = false;
    };
  }, []);

  const degradation = riskFlags.filter(
    (f) => f.level === "critical" || f.level === "warning"
  );

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Risk Controls"
        title="Risk Management"
        description="Exposure, volatility regime, drawdown limits and the position-sizing rules the strategy obeys."
        actions={
          <>
            <Badge variant={live ? "bull" : "outline"} className="hidden sm:inline-flex">
              <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
              {live ? "Live risk" : "Sample data"}
            </Badge>
            <Badge variant="bear">Elevated regime</Badge>
          </>
        }
      />

      {/* Top alert banner */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="relative overflow-hidden rounded-2xl border border-hold/30 bg-gradient-to-r from-hold/[0.1] to-transparent p-5"
      >
        <div className="absolute inset-y-0 left-0 w-1 bg-hold" />
        <div className="flex items-start gap-4">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl border border-hold/30 bg-hold/10">
            <ShieldAlert className="size-5 text-hold-soft" />
          </span>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-white">Risk Alert</h2>
              <Badge variant="hold">Auto-applied</Badge>
            </div>
            <p className="mt-1 max-w-2xl text-sm text-slate-300">
              Current volatility regime is elevated. QuantML has reduced suggested
              position sizing by{" "}
              <span className="font-semibold text-hold-soft">35%</span> and paused
              new entries above the 90th-percentile volatility threshold.
            </p>
          </div>
        </div>
      </motion.div>

      {/* Exposure donuts */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <DonutCard title="Exposure by Asset" data={exposureByAsset} />
        <DonutCard title="Exposure by Sector" data={exposureBySector} />
      </div>

      {/* Volatility + budget */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <GlassPanel strong className="xl:col-span-2">
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
            <div>
              <h3 className="text-sm font-semibold text-white">
                Volatility Regime
              </h3>
              <p className="text-[11px] text-slate-500">
                Implied (VIX) vs realized · 40 sessions
              </p>
            </div>
            <div className="flex items-center gap-3 font-mono text-[10px]">
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="size-2 rounded-full bg-hold" /> Implied
              </span>
              <span className="flex items-center gap-1.5 text-slate-400">
                <span className="size-2 rounded-full bg-brand-400" /> Realized
              </span>
            </div>
          </div>
          <div className="p-4">
            <VolatilityChart height={260} data={volatilityRegime} />
          </div>
        </GlassPanel>

        <GlassPanel strong>
          <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
            <Gauge className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">Risk Budget</h3>
          </div>
          <div className="space-y-4 p-5">
            {riskBudget.map((b, i) => {
              const pct = (b.used / b.limit) * 100;
              const hot = pct > 85;
              return (
                <div key={b.label}>
                  <div className="mb-1.5 flex items-center justify-between text-xs">
                    <span className="text-slate-400">{b.label}</span>
                    <span className="font-mono text-slate-300 data">
                      {b.used} / {b.limit}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/8">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${Math.min(pct, 100)}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.9, delay: i * 0.08, ease: "easeOut" }}
                      className={cn(
                        "h-full rounded-full",
                        hot ? "bg-bear" : pct > 65 ? "bg-hold" : "bg-brand-400"
                      )}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </GlassPanel>
      </div>

      {/* Rules + degradation */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <GlassPanel strong>
          <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
            <ListChecks className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">
              Position Sizing Rules
            </h3>
          </div>
          <ul className="space-y-3 p-5">
            {positionRules.map((r, i) => (
              <motion.li
                key={i}
                initial={{ opacity: 0, x: 8 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="flex gap-3 text-sm text-slate-300"
              >
                <span className="mt-0.5 grid size-5 shrink-0 place-items-center rounded-md border border-brand-400/25 bg-brand-500/10 font-mono text-[10px] text-brand-200">
                  {i + 1}
                </span>
                {r}
              </motion.li>
            ))}
          </ul>
        </GlassPanel>

        <GlassPanel strong>
          <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
            <h3 className="text-sm font-semibold text-white">
              Drift & Degradation
            </h3>
            <Badge variant="bear">{degradation.length} active</Badge>
          </div>
          <div className="space-y-2.5 p-4">
            {riskFlags.map((f, i) => (
              <RiskAlert key={f.id} flag={f} index={i} />
            ))}
          </div>
        </GlassPanel>
      </div>
    </PageTransition>
  );
}
