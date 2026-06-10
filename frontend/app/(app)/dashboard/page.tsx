"use client";

import { useEffect, useState } from "react";
import { Download, TrendingUp } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { MetricCard } from "@/components/metric-card";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import { DrawdownChart } from "@/components/charts/drawdown-chart";
import { SignalsTable } from "@/components/signals-table";
import { ResearchAssistant } from "@/components/research-assistant";
import { RiskAlert } from "@/components/risk-alert";
import { api } from "@/lib/api";
import {
  dashboardMetrics,
  equitySeries,
  riskFlags as mockRiskFlags,
  signals as mockSignals,
  type MetricPoint,
  type RiskFlag,
  type Signal,
} from "@/lib/mock-data";

type KpiMetric = {
  key: string;
  label: string;
  value: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  delta: number;
  spark: number;
  up: boolean;
};

function PanelTitle({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-white/6 px-5 py-3.5">
      <div>
        <h3 className="text-sm font-semibold text-white">{title}</h3>
        {subtitle && <p className="text-[11px] text-slate-500">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

export default function DashboardPage() {
  const [signals, setSignals] = useState<Signal[]>(mockSignals);
  const [flags, setFlags] = useState<RiskFlag[]>(mockRiskFlags);
  const [metrics, setMetrics] = useState<KpiMetric[]>(
    dashboardMetrics as unknown as KpiMetric[]
  );
  const [equity, setEquity] = useState<MetricPoint[]>(equitySeries);
  const [live, setLive] = useState(false);
  const [perfLive, setPerfLive] = useState(false);

  useEffect(() => {
    let active = true;
    api
      .signals()
      .then((d) => {
        if (active && Array.isArray(d) && d.length) {
          setSignals(d as Signal[]);
          setLive(true);
        }
      })
      .catch(() => {
        /* keep mock fallback */
      });
    api
      .risk()
      .then((d) => {
        if (active && d && Array.isArray(d.flags) && d.flags.length) {
          setFlags(d.flags as RiskFlag[]);
        }
      })
      .catch(() => {
        /* keep mock fallback */
      });
    api
      .metrics()
      .then((d) => {
        if (active && Array.isArray(d) && d.length) {
          setMetrics(d as KpiMetric[]);
          setPerfLive(true);
        }
      })
      .catch(() => {
        /* keep mock fallback */
      });
    api
      .equity()
      .then((d) => {
        if (active && Array.isArray(d) && d.length) setEquity(d);
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
        eyebrow="Command Centre"
        title="Overview"
        description="Live snapshot of strategy performance, model health and risk posture."
        actions={
          <>
            <Button variant="secondary" size="sm">
              <Download className="size-4" /> Export
            </Button>
            <Button size="sm">
              <TrendingUp className="size-4" /> Run Backtest
            </Button>
          </>
        }
      />

      {/* Metrics grid */}
      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        {metrics.map((m, i) => (
          <MetricCard
            key={m.key}
            label={m.label}
            value={m.value}
            decimals={m.decimals}
            prefix={m.prefix ?? ""}
            suffix={m.suffix ?? ""}
            delta={m.delta}
            positiveIsGood={m.key !== "drawdown" && m.key !== "exposure"}
            sparkSeed={m.spark}
            sparkUp={m.up}
            index={i}
          />
        ))}
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* Left / centre */}
        <div className="space-y-6 xl:col-span-2">
          <GlassPanel strong>
            <PanelTitle
              title="Equity Curve"
              subtitle="Walk-forward backtest · net of costs · rebased to 100"
            >
              <div className="flex items-center gap-3">
                <Badge variant={perfLive ? "bull" : "outline"}>
                  <span className={`size-1.5 rounded-full ${perfLive ? "bg-bull" : "bg-slate-500"}`} />
                  {perfLive ? "Live backtest" : "Sample data"}
                </Badge>
                <div className="hidden items-center gap-3 font-mono text-[10px] sm:flex">
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <span className="size-2 rounded-full bg-brand-400" /> Strategy
                  </span>
                  <span className="flex items-center gap-1.5 text-slate-400">
                    <span className="size-2 rounded-full bg-violet-glow" /> QQQ
                  </span>
                </div>
              </div>
            </PanelTitle>
            <div className="p-4">
              <EquityCurveChart height={300} data={equity} />
            </div>
          </GlassPanel>

          <GlassPanel strong>
            <PanelTitle title="Drawdown" subtitle="Underwater curve · peak-to-trough" />
            <div className="p-4">
              <DrawdownChart height={180} data={equity} />
            </div>
          </GlassPanel>

          <GlassPanel strong>
            <PanelTitle title="Latest Signals" subtitle="Model-generated · research output, not advice">
              <Badge variant={live ? "bull" : "outline"}>
                <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
                {live ? "Live model" : "Sample data"}
              </Badge>
            </PanelTitle>
            <div className="p-2 sm:p-3">
              <SignalsTable data={signals} limit={6} />
            </div>
          </GlassPanel>
        </div>

        {/* Right rail */}
        <div className="space-y-6">
          <ResearchAssistant compact />

          <GlassPanel strong>
            <PanelTitle title="Risk & Model Alerts" subtitle="Auto-generated by the risk layer">
              <Badge variant={flags.length ? "bear" : "outline"}>{flags.length} active</Badge>
            </PanelTitle>
            <div className="space-y-2.5 p-4">
              {flags.map((f, i) => (
                <RiskAlert key={f.id} flag={f} index={i} />
              ))}
            </div>
          </GlassPanel>
        </div>
      </div>
    </PageTransition>
  );
}
