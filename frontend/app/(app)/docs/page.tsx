import {
  Database,
  SlidersHorizontal,
  Target,
  CalendarRange,
  Receipt,
  Activity,
  Bot,
  AlertTriangle,
} from "lucide-react";
import { PageTransition, FadeIn } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { GlassPanel } from "@/components/glass-panel";
import { Badge } from "@/components/ui/badge";

const SECTIONS = [
  {
    id: "data-ingestion",
    icon: Database,
    title: "Data Ingestion",
    body: "QuantML ingests daily OHLCV data and corporate fundamentals for the configured universe (default: NASDAQ 100). Data is point-in-time aligned to avoid look-ahead bias — only information available at the close of session t is used to predict t+1…t+5. Corporate actions (splits, dividends) are adjusted, and survivorship-bias-free constituent histories are used where available.",
    bullets: [
      "Point-in-time joins prevent look-ahead leakage.",
      "Split/dividend adjusted price series.",
      "Configurable universe and date range.",
    ],
  },
  {
    id: "feature-engineering",
    icon: SlidersHorizontal,
    title: "Feature Engineering",
    body: "The feature engine derives ~84 technical and factor features per name: momentum across multiple horizons, relative strength versus sector, volume z-scores, volatility-regime indicators, mean-reversion signals, options-derived skew, and macro factors such as rates. Features are computed causally and standardised cross-sectionally within each rebalance window.",
    bullets: [
      "Cross-sectional standardisation per rebalance.",
      "Technical, factor, options and macro families.",
      "Causal computation — no future bars used.",
    ],
  },
  {
    id: "target-definition",
    icon: Target,
    title: "Target Definition",
    body: "The model predicts a probabilistic 5-day forward outlook, discretised into BUY / HOLD / AVOID. Targets are forward returns net of a neutral band to avoid trading noise. Class thresholds are calibrated on the training fold only, then frozen for the out-of-sample evaluation window.",
    bullets: [
      "5-day forward return with a neutral dead-band.",
      "Probability calibration on training folds only.",
      "Three-state output: BUY / HOLD / AVOID.",
    ],
  },
  {
    id: "walk-forward",
    icon: CalendarRange,
    title: "Walk-Forward Validation",
    body: "Models are evaluated with expanding-window walk-forward validation (12 folds). Each fold trains on all data up to time t and tests strictly on the subsequent out-of-sample period. This mirrors how a model would be retrained and deployed in production and is far more honest than a single random train/test split.",
    bullets: [
      "Expanding-window, 12-fold walk-forward.",
      "Strictly out-of-sample test periods.",
      "Mirrors a real retraining cadence.",
    ],
  },
  {
    id: "transaction-costs",
    icon: Receipt,
    title: "Transaction Costs & Slippage",
    body: "All backtests apply configurable transaction costs (default 5 bps) and slippage (default 8 bps) on every fill. Turnover is tracked explicitly because a strategy that looks profitable gross of costs can be unviable net of them. Cost assumptions are surfaced in every report so results are reproducible.",
    bullets: [
      "Per-fill commission and slippage in bps.",
      "Turnover tracked and reported.",
      "Net-of-cost performance is the headline.",
    ],
  },
  {
    id: "risk-metrics",
    icon: Activity,
    title: "Risk Metrics",
    body: "Performance is summarised with Sharpe and Sortino ratios, annualised volatility, maximum drawdown, win rate, profit factor and exposure/turnover. The risk layer enforces single-name and sector caps, volatility-scaled position sizing, and soft/hard drawdown stops before any signal becomes a suggested position.",
    bullets: [
      "Sharpe, Sortino, volatility, max drawdown.",
      "Single-name and sector exposure caps.",
      "Volatility-scaled sizing with drawdown stops.",
    ],
  },
  {
    id: "rag-assistant",
    icon: Bot,
    title: "RAG Research Assistant",
    body: "The research assistant uses retrieval-augmented generation over filings, news, earnings transcripts and internal model reports (SHAP attributions, drift logs, backtest summaries). It explains why a signal fired, surfaces contradicting risks, and cites every source. It is an explanation layer — it does not place trades or provide financial advice.",
    bullets: [
      "Grounded in filings, news, earnings, model reports.",
      "Cites sources and shows model signal context.",
      "Explains — never executes — decisions.",
    ],
  },
];

export default function DocsPage() {
  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Methodology"
        title="Documentation"
        description="How QuantML turns market data into evaluated, explainable ML trading research — and the limits of what that means."
        actions={<Badge variant="brand">v0.1</Badge>}
      />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-4">
        {/* TOC */}
        <aside className="lg:col-span-1">
          <div className="lg:sticky lg:top-28">
            <GlassPanel inset>
              <p className="label-eyebrow mb-3">On this page</p>
              <nav className="space-y-1">
                {SECTIONS.map((s) => (
                  <a
                    key={s.id}
                    href={`#${s.id}`}
                    className="block rounded-lg px-3 py-1.5 text-sm text-slate-400 transition-colors hover:bg-white/[0.04] hover:text-slate-100"
                  >
                    {s.title}
                  </a>
                ))}
                <a
                  href="#limitations"
                  className="block rounded-lg px-3 py-1.5 text-sm text-bear-soft/80 transition-colors hover:bg-white/[0.04] hover:text-bear-soft"
                >
                  Limitations & Disclaimers
                </a>
              </nav>
            </GlassPanel>
          </div>
        </aside>

        {/* Content */}
        <div className="space-y-5 lg:col-span-3">
          {SECTIONS.map((s, i) => {
            const Icon = s.icon;
            return (
              <FadeIn key={s.id} delay={i * 0.03}>
                <GlassPanel strong inset id={s.id} className="scroll-mt-28">
                  <div className="flex items-center gap-3">
                    <span className="grid size-10 place-items-center rounded-xl border border-brand-400/25 bg-brand-500/10">
                      <Icon className="size-5 text-brand-300" />
                    </span>
                    <h2 className="text-lg font-semibold text-white">{s.title}</h2>
                  </div>
                  <p className="mt-4 text-sm leading-relaxed text-slate-300">
                    {s.body}
                  </p>
                  <ul className="mt-4 grid gap-2 sm:grid-cols-3">
                    {s.bullets.map((b) => (
                      <li
                        key={b}
                        className="rounded-lg border border-white/6 bg-white/[0.02] px-3 py-2 text-xs text-slate-400"
                      >
                        {b}
                      </li>
                    ))}
                  </ul>
                </GlassPanel>
              </FadeIn>
            );
          })}

          {/* Limitations */}
          <FadeIn>
            <GlassPanel
              id="limitations"
              className="scroll-mt-28 border-bear/25 p-6"
            >
              <div className="flex items-center gap-3">
                <span className="grid size-10 place-items-center rounded-xl border border-bear/30 bg-bear/10">
                  <AlertTriangle className="size-5 text-bear-soft" />
                </span>
                <h2 className="text-lg font-semibold text-white">
                  Limitations & Disclaimers
                </h2>
              </div>
              <div className="mt-4 space-y-3 text-sm leading-relaxed text-slate-300">
                <p>
                  QuantML is a research and educational platform. It does not
                  provide financial advice, execute trades, or guarantee
                  profitable outcomes. All signals are experimental and should be
                  evaluated through rigorous backtesting and paper trading before
                  any real-world use.
                </p>
                <p>
                  Backtested performance is hypothetical, reflects the specific
                  assumptions documented above, and does not represent realised
                  returns. Markets regime-shift; a model that validated
                  out-of-sample can still degrade live, which is precisely why
                  drift monitoring and the risk layer exist.
                </p>
                <p className="text-slate-400">
                  Past performance is not indicative of future results. Nothing
                  here is an offer or solicitation to buy or sell any security.
                </p>
              </div>
            </GlassPanel>
          </FadeIn>
        </div>
      </div>
    </PageTransition>
  );
}
