import { seeded } from "./utils";

/**
 * Mock data layer.
 *
 * Everything here is seeded and deterministic so the server and client render
 * identical values and there are no hydration mismatches. Each export matches a
 * shape a future FastAPI backend can return, so swapping import for fetch later
 * is mechanical. lib/api.ts is the client surface this is standing in for.
 */

export type SignalType = "BUY" | "HOLD" | "AVOID";
export type RiskLevel = "Low" | "Moderate" | "High" | "Elevated";

export interface Signal {
  ticker: string;
  company: string;
  signal: SignalType;
  confidence: number; // 0-100
  expectedReturn5d: number; // percent
  risk: RiskLevel;
  model: string;
  drivers: string[];
  price: number;
  change: number; // percent intraday
  sector: string;
}

export interface MetricPoint {
  date: string;
  strategy: number;
  benchmark: number;
  drawdown: number;
}

export interface ModelRecord {
  id: string;
  name: string;
  family: string;
  status: "Production candidate" | "Champion" | "Experimental" | "Baseline" | "Archived";
  trainingWindow: string;
  validation: string;
  sharpe: number;
  cagr: number;
  maxDrawdown: number;
  drift: "Low" | "Medium" | "High";
  auc: number;
  accuracy: number;
  features: number;
  lastTrained: string;
  experimentId: string;
}

export interface Trade {
  id: string;
  date: string;
  ticker: string;
  side: "LONG" | "SHORT";
  entry: number;
  exit: number;
  pnl: number;
  ret: number;
  hold: number;
}

export interface RiskFlag {
  id: string;
  level: "info" | "warning" | "critical";
  title: string;
  detail: string;
  metric?: string;
}

/* ------------------------------------------------------------------ */
/* Time series                                                         */
/* ------------------------------------------------------------------ */

function buildSeries(points: number): MetricPoint[] {
  const rand = seeded(42);
  const series: MetricPoint[] = [];
  let strat = 100;
  let bench = 100;
  let peak = 100;
  const start = new Date(2024, 0, 1).getTime();

  for (let i = 0; i < points; i++) {
    // Strategy: positive drift, controlled vol
    strat *= 1 + (rand() - 0.46) * 0.018 + 0.0011;
    // Benchmark: lower drift, similar vol
    bench *= 1 + (rand() - 0.48) * 0.016 + 0.0006;

    peak = Math.max(peak, strat);
    const dd = ((strat - peak) / peak) * 100;

    const d = new Date(start + i * 86400000 * 3);
    series.push({
      date: d.toISOString().slice(0, 10),
      strategy: Number(strat.toFixed(2)),
      benchmark: Number(bench.toFixed(2)),
      drawdown: Number(dd.toFixed(2)),
    });
  }
  return series;
}

export const equitySeries = buildSeries(180);

export const equitySeriesShort = equitySeries.slice(-60);

/** Mini sparkline data for metric cards. */
export function sparkline(seed: number, n = 24, up = true): { v: number }[] {
  const rand = seeded(seed);
  let v = 50;
  const out: { v: number }[] = [];
  for (let i = 0; i < n; i++) {
    v += (rand() - (up ? 0.42 : 0.58)) * 9;
    v = Math.max(8, Math.min(95, v));
    out.push({ v: Number(v.toFixed(2)) });
  }
  return out;
}

/* ------------------------------------------------------------------ */
/* Top-level dashboard metrics                                         */
/* ------------------------------------------------------------------ */

// Real headline KPIs from the net-of-cost backtest (data/backtests/latest.json).
export const dashboardMetrics = [
  { key: "portfolio", label: "Backtest Value", value: 2119600, prefix: "$", decimals: 0, delta: 112.0, spark: 1, up: true },
  { key: "strategy", label: "Strategy Return", value: 112.0, suffix: "%", decimals: 1, delta: 18.5, spark: 2, up: true },
  { key: "benchmark", label: "Benchmark (QQQ)", value: 90.5, suffix: "%", decimals: 1, delta: 15.7, spark: 3, up: true },
  { key: "sharpe", label: "Sharpe Ratio", value: 0.88, decimals: 2, delta: 1.24, spark: 4, up: true },
  { key: "drawdown", label: "Max Drawdown", value: -29.7, suffix: "%", decimals: 1, delta: -29.7, spark: 5, up: false },
  { key: "winrate", label: "Win Rate", value: 57.8, suffix: "%", decimals: 1, delta: 7.8, spark: 6, up: true },
  { key: "confidence", label: "Model Confidence", value: 41, suffix: "%", decimals: 0, delta: -9, spark: 7, up: false },
  { key: "exposure", label: "Gross Exposure", value: 85, suffix: "%", decimals: 0, delta: -15, spark: 8, up: false },
] as const;

/* ------------------------------------------------------------------ */
/* Signals                                                             */
/* ------------------------------------------------------------------ */

export const signals: Signal[] = [
  {
    ticker: "NVDA",
    company: "NVIDIA Corp.",
    signal: "BUY",
    confidence: 78,
    expectedReturn5d: 2.1,
    risk: "High",
    model: "XGBoost-v3",
    drivers: ["Momentum (20d)", "Volume spike", "Relative strength", "Earnings revision"],
    price: 121.4,
    change: 1.8,
    sector: "Semiconductors",
  },
  {
    ticker: "MSFT",
    company: "Microsoft Corp.",
    signal: "HOLD",
    confidence: 54,
    expectedReturn5d: 0.4,
    risk: "Low",
    model: "XGBoost-v3",
    drivers: ["Trend stability", "Low volatility", "Neutral flow"],
    price: 441.2,
    change: 0.3,
    sector: "Software",
  },
  {
    ticker: "AAPL",
    company: "Apple Inc.",
    signal: "BUY",
    confidence: 66,
    expectedReturn5d: 1.3,
    risk: "Moderate",
    model: "XGBoost-v3",
    drivers: ["Mean reversion", "Options skew", "Seasonality"],
    price: 228.9,
    change: 0.9,
    sector: "Hardware",
  },
  {
    ticker: "AMZN",
    company: "Amazon.com Inc.",
    signal: "HOLD",
    confidence: 51,
    expectedReturn5d: -0.2,
    risk: "Moderate",
    model: "XGBoost-v3",
    drivers: ["Range-bound", "Soft volume", "Macro overhang"],
    price: 186.3,
    change: -0.4,
    sector: "E-commerce",
  },
  {
    ticker: "TSLA",
    company: "Tesla Inc.",
    signal: "AVOID",
    confidence: 71,
    expectedReturn5d: -1.6,
    risk: "Elevated",
    model: "XGBoost-v3",
    drivers: ["Negative momentum", "Elevated IV", "Deteriorating breadth"],
    price: 246.7,
    change: -2.7,
    sector: "Automotive",
  },
  {
    ticker: "GOOGL",
    company: "Alphabet Inc.",
    signal: "BUY",
    confidence: 63,
    expectedReturn5d: 1.1,
    risk: "Moderate",
    model: "XGBoost-v3",
    drivers: ["Breakout", "Positive drift", "Sector rotation"],
    price: 178.5,
    change: 1.2,
    sector: "Software",
  },
  {
    ticker: "META",
    company: "Meta Platforms",
    signal: "BUY",
    confidence: 69,
    expectedReturn5d: 1.7,
    risk: "Moderate",
    model: "XGBoost-v3",
    drivers: ["Momentum (60d)", "Earnings beat", "Flow imbalance"],
    price: 504.1,
    change: 1.5,
    sector: "Software",
  },
  {
    ticker: "AMD",
    company: "Advanced Micro Devices",
    signal: "AVOID",
    confidence: 58,
    expectedReturn5d: -0.9,
    risk: "High",
    model: "XGBoost-v3",
    drivers: ["Weak relative strength", "Distribution days"],
    price: 158.2,
    change: -1.9,
    sector: "Semiconductors",
  },
];

/* ------------------------------------------------------------------ */
/* Models                                                              */
/* ------------------------------------------------------------------ */

// Real champion + baselines from the walk-forward run (data/models/model_card.json).
// The Next.js route handlers serve the live snapshot; this stays in sync as the fallback.
export const models: ModelRecord[] = [
  {
    id: "xgboost-v3",
    name: "XGBoost-v3",
    family: "Gradient Boosting",
    status: "Champion",
    trainingWindow: "2019 – 2026",
    validation: "6-fold walk-forward",
    sharpe: 1.19,
    cagr: 31.2,
    maxDrawdown: -29.3,
    drift: "Low",
    auc: 0.54,
    accuracy: 0.366,
    features: 24,
    lastTrained: "2026-06-12",
    experimentId: "exp-2026-06-12-xgb",
  },
  {
    id: "random-forest",
    name: "Random Forest",
    family: "Bagged Trees",
    status: "Baseline",
    trainingWindow: "2019 – 2026",
    validation: "6-fold walk-forward",
    sharpe: 0.99,
    cagr: 27.4,
    maxDrawdown: -38.0,
    drift: "Low",
    auc: 0.552,
    accuracy: 0.378,
    features: 24,
    lastTrained: "2026-06-12",
    experimentId: "exp-2026-06-12-rf",
  },
  {
    id: "cross-sectional-momentum",
    name: "Cross-sectional Momentum",
    family: "Rule-based",
    status: "Baseline",
    trainingWindow: "2019 – 2026",
    validation: "6-fold walk-forward",
    sharpe: 0.89,
    cagr: 21.6,
    maxDrawdown: -38.9,
    drift: "Low",
    auc: 0.507,
    accuracy: 0.345,
    features: 24,
    lastTrained: "2026-06-12",
    experimentId: "exp-2026-06-12-mom",
  },
  {
    id: "logistic-regression",
    name: "Logistic Regression",
    family: "Linear",
    status: "Baseline",
    trainingWindow: "2019 – 2026",
    validation: "6-fold walk-forward",
    sharpe: 0.85,
    cagr: 21.9,
    maxDrawdown: -38.5,
    drift: "Low",
    auc: 0.547,
    accuracy: 0.373,
    features: 24,
    lastTrained: "2026-06-12",
    experimentId: "exp-2026-06-12-logreg",
  },
];

export const featureImportance = [
  { feature: "Momentum 20d", importance: 0.182 },
  { feature: "Relative strength", importance: 0.146 },
  { feature: "Volume z-score", importance: 0.121 },
  { feature: "Volatility regime", importance: 0.104 },
  { feature: "Earnings revision", importance: 0.089 },
  { feature: "Options skew", importance: 0.077 },
  { feature: "Sector breadth", importance: 0.066 },
  { feature: "Mean reversion 5d", importance: 0.058 },
  { feature: "Macro factor (rates)", importance: 0.049 },
  { feature: "Liquidity score", importance: 0.041 },
];

export interface ModelVersion {
  id: string;
  version: string;
  name: string;
  family: string;
  status: "champion" | "archived" | "candidate";
  metrics: { sharpe?: number; auc?: number; cagr?: number; maxDrawdown?: number };
  trainWindow: string;
  features?: number;
  dsr: number | null;
  gatePassed: boolean;
  registeredAt: string;
  promotedAt: string | null;
}

// The real registry (data/models/registry.json): one DSR-gated champion so far.
export const modelRegistry: { versions: ModelVersion[]; championId: string } = {
  championId: "9f835283be",
  versions: [
    {
      id: "9f835283be", version: "v1", name: "XGBoost-v3", family: "Gradient Boosting",
      status: "champion", metrics: { sharpe: 1.19, auc: 0.54, cagr: 31.2, maxDrawdown: -29.3 },
      trainWindow: "2019 – 2026", features: 24, dsr: 1.0, gatePassed: true,
      registeredAt: "2026-06-17", promotedAt: "2026-06-17",
    },
  ],
};

/* ------------------------------------------------------------------ */
/* Backtests                                                           */
/* ------------------------------------------------------------------ */

// Real net-of-cost backtest summary (data/backtests/latest.json).
export const backtestMetrics = [
  { label: "CAGR", value: "18.5%", tone: "bull" as const },
  { label: "Sharpe Ratio", value: "0.88", tone: "neutral" as const },
  { label: "Sortino Ratio", value: "1.24", tone: "neutral" as const },
  { label: "Max Drawdown", value: "-29.7%", tone: "bear" as const },
  { label: "Volatility (ann.)", value: "22.0%", tone: "neutral" as const },
  { label: "Turnover", value: "4682%", tone: "neutral" as const },
  { label: "Win Rate", value: "57.8%", tone: "bull" as const },
  { label: "Profit Factor", value: "1.52", tone: "bull" as const },
];

export const monthlyReturns: { year: number; months: (number | null)[] }[] = (() => {
  const rand = seeded(7);
  const years = [2021, 2022, 2023, 2024, 2025, 2026];
  return years.map((year) => ({
    year,
    months: Array.from({ length: 12 }, (_, m) => {
      if (year === 2026 && m > 5) return null;
      const base = (rand() - 0.42) * 9;
      return Number(base.toFixed(1));
    }),
  }));
})();

export const trades: Trade[] = (() => {
  const rand = seeded(11);
  const tickers = ["NVDA", "MSFT", "AAPL", "AMZN", "TSLA", "GOOGL", "META", "AMD"];
  return Array.from({ length: 14 }, (_, i) => {
    const t = tickers[Math.floor(rand() * tickers.length)];
    const entry = 80 + rand() * 400;
    const ret = (rand() - 0.42) * 9;
    const exit = entry * (1 + ret / 100);
    const side = rand() > 0.22 ? "LONG" : "SHORT";
    const d = new Date(2026, 4, 28 - i);
    return {
      id: `T-${4200 - i}`,
      date: d.toISOString().slice(0, 10),
      ticker: t,
      side,
      entry: Number(entry.toFixed(2)),
      exit: Number(exit.toFixed(2)),
      pnl: Number(((exit - entry) * 100).toFixed(0)),
      ret: Number(ret.toFixed(2)),
      hold: Math.ceil(rand() * 9),
    } as Trade;
  });
})();

/* ------------------------------------------------------------------ */
/* Risk                                                                */
/* ------------------------------------------------------------------ */

export const exposureByAsset = [
  { name: "NVDA", value: 18 },
  { name: "MSFT", value: 14 },
  { name: "AAPL", value: 12 },
  { name: "META", value: 10 },
  { name: "GOOGL", value: 9 },
  { name: "AMZN", value: 7 },
  { name: "Cash", value: 30 },
];

export const exposureBySector = [
  { name: "Software", value: 33 },
  { name: "Semiconductors", value: 24 },
  { name: "Hardware", value: 12 },
  { name: "E-commerce", value: 9 },
  { name: "Cash", value: 22 },
];

export const volatilityRegime = (() => {
  const rand = seeded(19);
  return Array.from({ length: 40 }, (_, i) => ({
    t: i,
    vix: Number((14 + Math.sin(i / 4) * 5 + rand() * 6).toFixed(2)),
    realized: Number((12 + Math.sin(i / 5 + 1) * 4 + rand() * 5).toFixed(2)),
  }));
})();

export const riskBudget = [
  { label: "Gross exposure", used: 64, limit: 100 },
  { label: "Single-name max", used: 18, limit: 20 },
  { label: "Sector max", used: 33, limit: 40 },
  { label: "Daily VaR (95%)", used: 1.9, limit: 2.5 },
  { label: "Beta to QQQ", used: 0.82, limit: 1.2 },
];

export const riskFlags: RiskFlag[] = [
  {
    id: "r1",
    level: "warning",
    title: "Elevated volatility regime",
    detail:
      "Realized 10-day volatility is in the 82nd percentile. Suggested position sizing reduced by 35%.",
    metric: "VIX 21.4 · +18% w/w",
  },
  {
    id: "r2",
    level: "warning",
    title: "Feature drift — XGBoost-v3",
    detail:
      "PSI on 'volume z-score' exceeded 0.21 against the training reference. Flagged for review.",
    metric: "PSI 0.21",
  },
  {
    id: "r3",
    level: "critical",
    title: "Drawdown threshold approaching",
    detail:
      "Strategy drawdown at -12.8% vs -15% soft stop. De-risking protocol armed.",
    metric: "-12.8% / -15.0%",
  },
  {
    id: "r4",
    level: "info",
    title: "Model retrain scheduled",
    detail: "XGBoost-v3 scheduled for walk-forward refit on 2026-06-15.",
    metric: "in 8 days",
  },
];

export const positionRules = [
  "Kelly-fraction sizing capped at 0.5× with volatility scaling.",
  "Per-name exposure hard cap at 20% of gross.",
  "Soft drawdown stop at -15%; full de-risk at -20%.",
  "Position sizing scales inversely with realized volatility regime.",
  "No new entries when realized vol > 90th percentile.",
];

/* ------------------------------------------------------------------ */
/* Research assistant (RAG)                                            */
/* ------------------------------------------------------------------ */

export interface RagSource {
  title: string;
  type: "Filing" | "News" | "Model report" | "Earnings" | "Research";
  date: string;
  snippet: string;
}

export interface RagResponse {
  prompt: string;
  answer: string;
  sources: RagSource[];
  signalContext: { ticker: string; signal: SignalType; confidence: number; model: string };
  riskWarnings: string[];
  confidence: number;
}

export const examplePrompts = [
  "Why did the model generate a BUY signal for NVDA?",
  "What risks contradict the current signal?",
  "Summarise the latest earnings context.",
  "Which features drove the latest prediction?",
  "How did similar signals perform historically?",
];

export const ragResponses: Record<string, RagResponse> = {
  default: {
    prompt: "Why did the model generate a BUY signal for NVDA?",
    answer:
      "XGBoost-v3 issued a BUY for NVDA with 78% confidence. The decision is dominated by strong 20-day momentum and a volume spike (+2.3σ vs trailing mean), reinforced by positive analyst earnings revisions over the past two weeks. Relative strength versus the semiconductor peer group sits in the 88th percentile. The model projects a +2.1% five-day forward return, though it flags the signal as High risk given elevated implied volatility.",
    sources: [
      {
        title: "NVDA Q1 FY26 earnings call transcript",
        type: "Earnings",
        date: "2026-05-22",
        snippet:
          "Data-center revenue grew 78% YoY; management guided above consensus on continued accelerator demand…",
      },
      {
        title: "Sell-side estimate revisions — Semis",
        type: "Research",
        date: "2026-05-30",
        snippet:
          "Consensus FY26 EPS revised +6.4% over trailing 14 days; 12 of 14 analysts raised targets…",
      },
      {
        title: "XGBoost-v3 SHAP attribution report",
        type: "Model report",
        date: "2026-06-06",
        snippet:
          "Top positive contributors: momentum_20d (+0.18), volume_z (+0.12), rel_strength (+0.11)…",
      },
    ],
    signalContext: { ticker: "NVDA", signal: "BUY", confidence: 78, model: "XGBoost-v3" },
    riskWarnings: [
      "Implied volatility in the 84th percentile — wider stop recommended.",
      "Signal is momentum-driven and may decay quickly on a regime shift.",
      "High concentration: NVDA already at 18% of gross exposure (cap 20%).",
    ],
    confidence: 78,
  },
  risks: {
    prompt: "What risks contradict the current signal?",
    answer:
      "Several factors push against the active BUY. First, the volatility regime is elevated (realized vol in the 82nd percentile), which historically compresses momentum-strategy Sharpe. Second, NVDA already represents 18% of gross exposure against a 20% single-name cap, leaving little room to add. Third, options skew has steepened, implying the market is paying up for downside protection. The model's confidence (78%) is meaningful but not extreme, and similar setups have a 57% historical hit rate.",
    sources: [
      {
        title: "Risk layer — exposure snapshot",
        type: "Model report",
        date: "2026-06-07",
        snippet: "NVDA 18.0% of gross · single-name cap 20% · sector (Semis) 24%…",
      },
      {
        title: "Volatility regime monitor",
        type: "Model report",
        date: "2026-06-07",
        snippet: "Realized 10d vol 82nd pct; suggested sizing multiplier 0.65×…",
      },
      {
        title: "Options analytics — NVDA skew",
        type: "News",
        date: "2026-06-05",
        snippet: "25-delta put-call skew steepened to +6.1 vol points week over week…",
      },
    ],
    signalContext: { ticker: "NVDA", signal: "BUY", confidence: 78, model: "XGBoost-v3" },
    riskWarnings: [
      "Elevated volatility regime — sizing automatically reduced 35%.",
      "Near single-name concentration cap.",
      "Steepening put skew signals hedging demand.",
    ],
    confidence: 64,
  },
};

export function getRagResponse(prompt: string): RagResponse {
  const p = prompt.toLowerCase();
  if (p.includes("risk") || p.includes("contradict")) return ragResponses.risks;
  return { ...ragResponses.default, prompt };
}

/* ------------------------------------------------------------------ */
/* Top status / market context                                        */
/* ------------------------------------------------------------------ */

export const marketContext = {
  market: "Open" as "Open" | "Closed",
  universe: "NASDAQ 100",
  model: "XGBoost-v3",
  lastUpdated: "16:00 ET",
  paperMode: true,
};

export const tickerTape = [
  { sym: "QQQ", price: 478.21, chg: 0.62 },
  { sym: "NVDA", price: 121.4, chg: 1.8 },
  { sym: "MSFT", price: 441.2, chg: 0.3 },
  { sym: "AAPL", price: 228.9, chg: 0.9 },
  { sym: "TSLA", price: 246.7, chg: -2.7 },
  { sym: "META", price: 504.1, chg: 1.5 },
  { sym: "AMD", price: 158.2, chg: -1.9 },
  { sym: "GOOGL", price: 178.5, chg: 1.2 },
  { sym: "AMZN", price: 186.3, chg: -0.4 },
  { sym: "VIX", price: 21.4, chg: 4.1 },
  { sym: "10Y", price: 4.28, chg: -0.6 },
  { sym: "BTC", price: 68420, chg: 2.3 },
];
