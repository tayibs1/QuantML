import Link from "next/link";
import {
  AlertOctagon,
  ArrowRight,
  Bot,
  Database,
  Eye,
  GitBranch,
  LineChart,
  Receipt,
  ShieldAlert,
  ShieldCheck,
  SlidersHorizontal,
  TrendingUp,
} from "lucide-react";
import { LandingNav } from "@/components/landing/landing-nav";
import { Hero } from "@/components/landing/hero";
import { SiteFooter } from "@/components/landing/site-footer";
import { ArchitectureFlow } from "@/components/architecture-flow";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MetricCard } from "@/components/metric-card";
import { EquityCurveChart } from "@/components/charts/equity-curve-chart";
import { SignalsTable } from "@/components/signals-table";
import { RiskAlert } from "@/components/risk-alert";
import { StaggerGroup, Reveal, FadeIn } from "@/components/motion-primitives";
import { dashboardMetrics, riskFlags } from "@/lib/mock-data";

const PROBLEMS = [
  { icon: Eye, title: "Look-ahead bias", desc: "Future data leaks into training and inflates results." },
  { icon: TrendingUp, title: "Overfitted backtests", desc: "Curves that only ever worked on the sample they were tuned on." },
  { icon: Receipt, title: "No transaction costs", desc: "Strategies that evaporate once spreads and slippage are real." },
  { icon: ShieldAlert, title: "No risk controls", desc: "Position sizing and drawdown limits treated as an afterthought." },
  { icon: AlertOctagon, title: "No model monitoring", desc: "Silent drift and signal decay long after deployment." },
  { icon: Bot, title: "No explanation layer", desc: "Black-box calls no one can interrogate or trust." },
];

const SOLUTIONS = [
  { icon: Database, title: "Market Data Pipeline", desc: "Ingest OHLCV data and generate technical and factor features, point-in-time aligned.", tag: "ingest" },
  { icon: SlidersHorizontal, title: "ML Signal Models", desc: "Train models to generate probabilistic buy / hold / avoid signals with calibrated confidence.", tag: "predict" },
  { icon: LineChart, title: "Walk-Forward Backtesting", desc: "Evaluate strategies out-of-sample with realistic transaction costs and slippage.", tag: "evaluate" },
  { icon: ShieldCheck, title: "Risk-Aware Evaluation", desc: "Measure Sharpe, drawdown, volatility, turnover and exposure — net of costs.", tag: "control" },
  { icon: Bot, title: "RAG Market Research", desc: "Explain signals using filings, news, model reports and financial context.", tag: "explain" },
  { icon: GitBranch, title: "Model Monitoring", desc: "Track feature drift, signal decay and live / paper-trading performance.", tag: "monitor" },
];

function SectionHeading({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: React.ReactNode;
  description?: string;
}) {
  return (
    <FadeIn className="mx-auto max-w-2xl text-center">
      <p className="label-eyebrow">{eyebrow}</p>
      <h2 className="mt-3 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
        {title}
      </h2>
      {description && (
        <p className="mt-4 text-base leading-relaxed text-slate-400">
          {description}
        </p>
      )}
    </FadeIn>
  );
}

export default function LandingPage() {
  return (
    <div className="relative min-h-screen">
      <LandingNav />
      <Hero />

      {/* Problem */}
      <section className="relative mx-auto max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="The Problem"
          title="Most trading models fail outside the notebook."
          description="The gap between a backtest that looks good and a strategy that survives contact with the market is where most quant projects quietly die."
        />
        <StaggerGroup className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {PROBLEMS.map((p) => {
            const Icon = p.icon;
            return (
              <Reveal key={p.title}>
                <GlassPanel glow inset className="group h-full">
                  <div className="flex items-center gap-3">
                    <span className="grid size-10 place-items-center rounded-xl border border-bear/20 bg-bear/[0.06] text-bear-soft transition-transform group-hover:scale-110">
                      <Icon className="size-5" />
                    </span>
                    <h3 className="font-semibold text-white">{p.title}</h3>
                  </div>
                  <p className="mt-3 text-sm leading-relaxed text-slate-400">
                    {p.desc}
                  </p>
                </GlassPanel>
              </Reveal>
            );
          })}
        </StaggerGroup>
      </section>

      {/* Solution */}
      <section id="solution" className="relative mx-auto max-w-6xl px-6 py-24">
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        <SectionHeading
          eyebrow="The Solution"
          title={
            <>
              QuantML turns trading ideas into{" "}
              <span className="text-gradient-brand">testable ML research</span>.
            </>
          }
          description="An end-to-end research workflow — from raw market data to explainable, risk-aware, continuously-monitored signals."
        />
        <StaggerGroup className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {SOLUTIONS.map((s) => {
            const Icon = s.icon;
            return (
              <Reveal key={s.title}>
                <GlassPanel glow inset className="group h-full">
                  <div className="flex items-start justify-between">
                    <span className="grid size-11 place-items-center rounded-xl border border-brand-400/25 bg-brand-500/10 text-brand-300 shadow-glow transition-transform group-hover:scale-110">
                      <Icon className="size-5" />
                    </span>
                    <Badge variant="outline">{s.tag}</Badge>
                  </div>
                  <h3 className="mt-4 text-lg font-semibold text-white">
                    {s.title}
                  </h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">
                    {s.desc}
                  </p>
                </GlassPanel>
              </Reveal>
            );
          })}
        </StaggerGroup>
      </section>

      {/* Architecture */}
      <section id="architecture" className="relative mx-auto max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="Architecture"
          title="A pipeline built like production software."
          description="Every stage is observable, testable and explainable — with a RAG assistant wired in to interpret what the model is doing."
        />
        <FadeIn className="mt-14">
          <GlassPanel strong className="relative overflow-hidden p-8 sm:p-12">
            <div className="pointer-events-none absolute inset-0 dots-overlay opacity-40" />
            <div className="relative">
              <ArchitectureFlow />
            </div>
          </GlassPanel>
        </FadeIn>
      </section>

      {/* Dashboard preview */}
      <section id="preview" className="relative mx-auto max-w-6xl px-6 py-24">
        <SectionHeading
          eyebrow="Live Preview"
          title="A command centre for signal research."
          description="Performance, signals, risk and AI research — in one institutional-grade terminal."
        />
        <FadeIn className="mt-12">
          <GlassPanel strong className="overflow-hidden">
            {/* Window chrome */}
            <div className="flex items-center gap-2 border-b border-white/6 px-4 py-3">
              <span className="size-3 rounded-full bg-bear/70" />
              <span className="size-3 rounded-full bg-hold/70" />
              <span className="size-3 rounded-full bg-bull/70" />
              <span className="ml-3 font-mono text-[11px] text-slate-500">
                quantml.app/dashboard
              </span>
              <Badge variant="brand" className="ml-auto">
                Live · paper
              </Badge>
            </div>

            <div className="space-y-5 p-4 sm:p-6">
              <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
                {dashboardMetrics.slice(0, 4).map((m, i) => (
                  <MetricCard
                    key={m.key}
                    label={m.label}
                    value={m.value}
                    decimals={m.decimals}
                    prefix={"prefix" in m ? (m.prefix as string) : ""}
                    suffix={"suffix" in m ? (m.suffix as string) : ""}
                    delta={m.delta}
                    positiveIsGood={m.key !== "drawdown"}
                    sparkSeed={m.spark}
                    sparkUp={m.up}
                    index={i}
                  />
                ))}
              </div>

              <div className="grid grid-cols-1 gap-5 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <GlassPanel className="h-full">
                    <div className="border-b border-white/6 px-5 py-3">
                      <h3 className="text-sm font-semibold text-white">
                        Equity Curve
                      </h3>
                    </div>
                    <div className="p-4">
                      <EquityCurveChart height={240} />
                    </div>
                  </GlassPanel>
                </div>
                <div className="space-y-3">
                  {riskFlags.slice(0, 3).map((f, i) => (
                    <RiskAlert key={f.id} flag={f} index={i} />
                  ))}
                </div>
              </div>

              <GlassPanel>
                <div className="border-b border-white/6 px-5 py-3">
                  <h3 className="text-sm font-semibold text-white">
                    Latest Signals
                  </h3>
                </div>
                <div className="p-2 sm:p-3">
                  <SignalsTable limit={4} />
                </div>
              </GlassPanel>
            </div>
          </GlassPanel>
        </FadeIn>
      </section>

      {/* CTA */}
      <section className="relative mx-auto max-w-5xl px-6 py-24">
        <FadeIn>
          <GlassPanel strong className="relative overflow-hidden p-10 text-center sm:p-16">
            <div className="pointer-events-none absolute -inset-x-20 -top-24 h-64 bg-brand-500/15 blur-3xl" />
            <div className="relative">
              <div className="space-y-1 text-2xl font-semibold tracking-tight text-white sm:text-4xl">
                <p>Research before you trade.</p>
                <p className="text-slate-400">Validate before you deploy.</p>
                <p className="text-gradient-brand">Explain before you trust.</p>
              </div>
              <p className="mx-auto mt-6 max-w-xl text-sm text-slate-400">
                Machine-learning trading research, evaluated like production
                software.
              </p>
              <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
                <Button asChild size="lg">
                  <Link href="/dashboard">
                    Open QuantML Dashboard <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg">
                  <Link href="/docs">Read the methodology</Link>
                </Button>
              </div>
            </div>
          </GlassPanel>
        </FadeIn>
      </section>

      <SiteFooter />
    </div>
  );
}
