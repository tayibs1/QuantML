"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { Settings2 } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import { DrawdownChart } from "@/components/charts/drawdown-chart";
import { MonthlyHeatmap } from "@/components/monthly-heatmap";
import { TradeHistoryTable } from "@/components/trade-history-table";
import { api } from "@/lib/api";
import {
  backtestMetrics,
  equitySeries,
  monthlyReturns as mockMonthly,
  trades as mockTrades,
  type MetricPoint,
  type Trade,
} from "@/lib/mock-data";
import { applyCostModel } from "@/lib/backtest-cost";
import { cn } from "@/lib/utils";

type Card = { label: string; value: string; tone: "bull" | "bear" | "neutral" };
type Rebalance = "Daily" | "Weekly" | "Monthly";

function LockedField({ label, value }: { label: string; value: string }) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <div className="flex items-center justify-between rounded-lg border border-white/8 bg-white/[0.02] px-3 py-2 text-sm text-slate-300">
        {value}
        <span className="font-mono text-[9px] uppercase tracking-wider text-slate-600">
          fixed
        </span>
      </div>
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <div className="relative">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
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

function Slider({
  label,
  value,
  max,
  suffix,
  onChange,
}: {
  label: string;
  value: number;
  max: number;
  suffix: string;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <span className="font-mono text-xs text-brand-200">
          {value}
          {suffix}
        </span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-white/10 accent-brand-400"
        style={{
          background: `linear-gradient(to right, #2dd4bf ${(value / max) * 100}%, rgba(255,255,255,0.1) 0)`,
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

  // knobs the user can change
  const [rebalance, setRebalance] = useState<Rebalance>("Weekly");
  const [txnCost, setTxnCost] = useState(5);
  const [slippage, setSlippage] = useState(8);

  // seeded with mock, swapped for the snapshot on mount
  const [cards, setCards] = useState<Card[]>(backtestMetrics as unknown as Card[]);
  const [equity, setEquity] = useState<MetricPoint[]>(equitySeries);
  const [tradeRows, setTradeRows] = useState<Trade[]>(mockTrades);
  const [monthly, setMonthly] = useState(mockMonthly);
  const [windowLabel, setWindowLabel] = useState("2021 – 2026");
  const [tradeCount, setTradeCount] = useState(mockTrades.length);
  const [live, setLive] = useState(false);

  const runBacktest = useCallback(async () => {
    try {
      const d = await api.backtests({
        rebalance,
        commissionBps: txnCost,
        slippageBps: slippage,
      });
      if (Array.isArray(d.summaryCards) && d.summaryCards.length)
        setCards(d.summaryCards as Card[]);
      if (Array.isArray(d.equity) && d.equity.length) setEquity(d.equity);
      if (Array.isArray(d.trades)) setTradeRows(d.trades);
      if (Array.isArray(d.monthlyReturns) && d.monthlyReturns.length)
        setMonthly(d.monthlyReturns);
      if (typeof d.tradeCount === "number") setTradeCount(d.tradeCount);
      if (d.window?.start) {
        const s = d.window.start.slice(0, 4);
        const e = d.window.end.slice(0, 4);
        setWindowLabel(`${s} – ${e}  ·  ${d.window.rebalances} rebalances`);
      }
      setLive(d.source === "live");
    } catch {
      /* keep mock fallback */
    }
  }, [rebalance, txnCost, slippage]);

  // initial load
  useEffect(() => {
    runBacktest();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // re-price the snapshot whenever a slider moves
  const view = useMemo(
    () =>
      applyCostModel(equity, cards, {
        commissionBps: txnCost,
        slippageBps: slippage,
        rebalance,
      }),
    [equity, cards, txnCost, slippage, rebalance]
  );

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Strategy Evaluation"
        title="Backtests"
        description="Walk-forward, out-of-sample evaluation. Net of costs, benchmarked against buy-and-hold QQQ."
        actions={
          <Badge variant={live ? "bull" : "outline"} className="hidden sm:inline-flex">
            <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
            {live ? "Live engine" : "Sample data"}
          </Badge>
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
            <LockedField label="Universe" value="NASDAQ 100 (56 names)" />
            <LockedField label="Model" value="XGBoost-v3 (walk-forward)" />
            <LockedField label="Out-of-sample window" value={windowLabel} />
            <SelectField
              label="Rebalance"
              value={rebalance}
              options={["Daily", "Weekly", "Monthly"]}
              onChange={(v) => setRebalance(v as Rebalance)}
            />
            <div className="hr-soft my-2" />
            <Slider
              label="Transaction cost"
              value={txnCost}
              max={30}
              suffix=" bps"
              onChange={setTxnCost}
            />
            <Slider
              label="Slippage"
              value={slippage}
              max={50}
              suffix=" bps"
              onChange={setSlippage}
            />
            <div className="hr-soft my-2" />
            <div className="flex items-center justify-between">
              <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
                Validation
              </span>
              <Badge variant="brand">Walk-forward</Badge>
            </div>
            <p className="pt-1 text-center font-mono text-[10px] uppercase tracking-wider text-slate-600">
              Results update live as you adjust
            </p>
          </div>
        </GlassPanel>

        {/* Results */}
        <div className="space-y-6 xl:col-span-3">
          {/* Metrics */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {view.summaryCards.map((m, i) => (
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
                <div>
                  <h3 className="text-sm font-semibold text-white">Performance</h3>
                  <p className="text-[11px] text-slate-500">
                    Strategy NAV vs QQQ · net of costs · rebased to 100
                  </p>
                </div>
                <TabsList>
                  <TabsTrigger value="equity">Equity</TabsTrigger>
                  <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
                  <TabsTrigger value="monthly">Monthly</TabsTrigger>
                </TabsList>
              </div>
              <div className="p-4">
                <TabsContent value="equity" className="mt-0">
                  <EquityCurveChart height={320} data={view.equity} />
                </TabsContent>
                <TabsContent value="drawdown" className="mt-0">
                  <DrawdownChart height={320} data={view.equity} />
                </TabsContent>
                <TabsContent value="monthly" className="mt-0">
                  <MonthlyHeatmap data={monthly} />
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
                  Closed long positions · most recent first
                </p>
              </div>
              <Badge variant="default">{tradeCount.toLocaleString()} trades</Badge>
            </div>
            <div className="p-2 sm:p-3">
              <TradeHistoryTable data={tradeRows} />
            </div>
          </GlassPanel>
        </div>
      </div>
    </PageTransition>
  );
}
