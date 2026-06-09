"use client";

import { useState } from "react";
import { motion } from "motion/react";
import { Play, Settings2, Download } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import { DrawdownChart } from "@/components/charts/drawdown-chart";
import { MonthlyHeatmap } from "@/components/monthly-heatmap";
import { TradeHistoryTable } from "@/components/trade-history-table";
import { backtestMetrics } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

function Field({
  label,
  value,
  options,
}: {
  label: string;
  value: string;
  options: string[];
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <div className="relative">
        <select
          defaultValue={value}
          className="w-full appearance-none rounded-lg border border-white/8 bg-white/[0.02] px-3 py-2 text-sm text-slate-200 transition-colors hover:border-white/15 focus:border-brand-400/40 focus:outline-none focus:ring-1 focus:ring-brand-400/20"
        >
          {options.map((o) => (
            <option key={o} value={o} className="bg-ink-850 text-slate-200">
              {o}
            </option>
          ))}
        </select>
        <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-slate-500">
          ▾
        </span>
      </div>
    </label>
  );
}

function Slider({ label, value, suffix }: { label: string; value: number; suffix: string }) {
  const [v, setV] = useState(value);
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <span className="font-mono text-xs text-brand-200">
          {v}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={label.includes("Slippage") ? 50 : 30}
        value={v}
        onChange={(e) => setV(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-brand-400"
        style={{
          background: `linear-gradient(to right, #2dd4bf ${(v / (label.includes("Slippage") ? 50 : 30)) * 100}%, rgba(255,255,255,0.1) 0)`,
        }}
      />
    </label>
  );
}

export default function BacktestsPage() {
  const toneClass = {
    bull: "text-bull-soft",
    bear: "text-bear-soft",
    neutral: "text-white",
  };

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Strategy Evaluation"
        title="Backtests"
        description="Walk-forward, out-of-sample evaluation with realistic transaction costs and slippage."
        actions={
          <>
            <Button variant="secondary" size="sm">
              <Download className="size-4" /> Report
            </Button>
            <Button size="sm">
              <Play className="size-4" /> Run Backtest
            </Button>
          </>
        }
      />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-4">
        {/* Config panel */}
        <GlassPanel strong className="h-fit xl:col-span-1">
          <div className="flex items-center gap-2 border-b border-white/6 px-5 py-3.5">
            <Settings2 className="size-4 text-brand-300" />
            <h3 className="text-sm font-semibold text-white">Configuration</h3>
          </div>
          <div className="space-y-4 p-5">
            <Field label="Universe" value="NASDAQ 100" options={["NASDAQ 100", "S&P 500", "Custom"]} />
            <Field label="Model" value="XGBoost-v3" options={["XGBoost-v3", "LightGBM-v2", "LSTM experimental"]} />
            <Field label="Period" value="2021–2026" options={["2021–2026", "2018–2026", "2023–2026"]} />
            <Field label="Rebalance" value="Weekly" options={["Daily", "Weekly", "Monthly"]} />
            <div className="hr-soft my-2" />
            <Slider label="Transaction cost" value={5} suffix=" bps" />
            <Slider label="Slippage" value={8} suffix=" bps" />
            <div className="hr-soft my-2" />
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Validation
              </span>
              <Badge variant="brand">Walk-forward</Badge>
            </div>
            <Button className="w-full">
              <Play className="size-4" /> Run Backtest
            </Button>
          </div>
        </GlassPanel>

        {/* Results */}
        <div className="space-y-6 xl:col-span-3">
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {backtestMetrics.map((m, i) => (
              <motion.div
                key={m.label}
                initial={{ opacity: 0, y: 14 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
              >
                <GlassPanel inset className="py-3.5">
                  <div className="text-[10px] uppercase tracking-wider text-slate-500">
                    {m.label}
                  </div>
                  <div
                    className={cn(
                      "mt-1 font-mono text-xl font-semibold data",
                      toneClass[m.tone]
                    )}
                  >
                    {m.value}
                  </div>
                </GlassPanel>
              </motion.div>
            ))}
          </div>

          {/* Charts */}
          <GlassPanel strong>
            <Tabs defaultValue="equity">
              <div className="flex items-center justify-between border-b border-white/6 px-5 py-3">
                <h3 className="text-sm font-semibold text-white">Performance</h3>
                <TabsList>
                  <TabsTrigger value="equity">Equity</TabsTrigger>
                  <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
                  <TabsTrigger value="monthly">Monthly</TabsTrigger>
                </TabsList>
              </div>
              <div className="p-4">
                <TabsContent value="equity" className="mt-0">
                  <EquityCurveChart height={320} />
                </TabsContent>
                <TabsContent value="drawdown" className="mt-0">
                  <DrawdownChart height={320} />
                </TabsContent>
                <TabsContent value="monthly" className="mt-0">
                  <MonthlyHeatmap />
                </TabsContent>
              </div>
            </Tabs>
          </GlassPanel>

          {/* Trade history */}
          <GlassPanel strong>
            <div className="flex items-center justify-between border-b border-white/6 px-5 py-3.5">
              <div>
                <h3 className="text-sm font-semibold text-white">Trade History</h3>
                <p className="text-[11px] text-slate-500">
                  Most recent closed positions
                </p>
              </div>
              <Badge variant="default">14 trades</Badge>
            </div>
            <div className="p-2 sm:p-3">
              <TradeHistoryTable />
            </div>
          </GlassPanel>
        </div>
      </div>
    </PageTransition>
  );
}
