/**
 * QuantML API client.
 *
 * Out of the box this hits the Next.js route handlers in app/api/* (same origin),
 * so the app really is fetching its data over HTTP, no separate process needed.
 * To point it at the Python FastAPI backend instead, set:
 *
 *     NEXT_PUBLIC_API_URL=http://localhost:8000
 *
 * The FastAPI endpoints return the same shapes, so nothing else has to change.
 * BACKEND.md has the full contract.
 */
import type {
  ModelRecord,
  RagResponse,
  RiskFlag,
  Signal,
  Trade,
  MetricPoint,
} from "./mock-data";

/** Config the Backtests page sends to POST /api/backtests. */
export interface BacktestConfig {
  rebalance?: "Daily" | "Weekly" | "Monthly";
  topN?: number;
  commissionBps?: number;
  slippageBps?: number;
  model?: string;
}

/** Full result returned by POST /api/backtests. */
export interface BacktestResult {
  source: "live" | "mock";
  config: Record<string, unknown>;
  window: { start: string; end: string; rebalances: number };
  metrics: Record<string, number> & {
    timeUnderWater?: { fraction: number; longestDays: number };
  };
  summaryCards: { label: string; value: string; tone: "bull" | "bear" | "neutral" }[];
  equity: MetricPoint[];
  trades: Trade[];
  tradeCount: number;
  monthlyReturns: { year: number; months: (number | null)[] }[];
  note?: string;
}

/** A single study's per-metric numbers (sharpe, auc, accuracy, hitRate, …). */
export type MetricBag = Record<string, number>;

/** Robustness studies returned by GET /api/validation. */
export interface ValidationStudies {
  rollingWindow: {
    note: string;
    generatedAt: string;
    baseline: MetricBag;
    rolling: MetricBag;
    weekly: { date: string; basketReturn: number; accuracy: number; nBuy: number; psi?: number }[];
  } | null;
  windowComparison: {
    note: string;
    generatedAt: string;
    step: number;
    windows: Record<string, MetricBag>;
    bestBySharpe: string | null;
    steadiestByVol: string | null;
  } | null;
  regimeModels: {
    general: MetricBag;
    ensemble: MetricBag;
    year2022: { general: number; ensemble: number };
    ensembleBeatsGeneral: boolean;
    verdict: string;
  } | null;
  ood: {
    trainEnd: string;
    trainRows: number;
    testRows: number;
    metrics: MetricBag;
    overallDrift: string;
    eraDrift: { feature: string; label: string; psi: number; status: string }[];
  } | null;
  confidence: {
    sizing: { equalWeight: MetricBag; confidenceWeighted: MetricBag };
    confidenceImprovesSharpe: boolean;
    calibration: { brier: number; ece: number; bins: { pMean: number; observed: number; n: number }[] };
  } | null;
  onlineLearning: {
    cadences: Record<string, { refitEvery: number; refits: number; seconds: number; sharpe: number; hitRate: number; weeks: number }>;
    fullRetrainSharpe: number | null;
  } | null;
}

/** Aggregated risk summary returned by GET /api/risk. */
export interface RiskSummary {
  flags: RiskFlag[];
  budget: { label: string; used: number; limit: number }[];
  exposureByAsset: { name: string; value: number }[];
  exposureBySector: { name: string; value: number }[];
  volatilityRegime: { t: number; vix: number; realized: number }[];
  positionRules: string[];
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";
const API_TIMEOUT_MS = 2000;  // 2 second timeout - if backend is slow, fall back to mock
// The research assistant is allowed longer: retrieval is fast, but a real LLM
// answer takes seconds, and cutting it off would drop the demo to the fallback.
const RESEARCH_TIMEOUT_MS = 45000;

export type SignalType = "BUY" | "HOLD" | "AVOID";

export interface ReplayPoint {
  date: string;
  value: number; // stock, rebased to 100 at entry
  bench: number | null; // QQQ, rebased to 100 at entry
}

export interface ReplayScenario {
  id: string;
  signal: SignalType;
  ticker: string;
  company: string;
  sector: string;
  entryDate: string;
  exitDate: string;
  entryPrice: number;
  exitPrice: number;
  ret: number;
  benchRet: number | null;
  notional: number;
  endValue: number;
  holdDays: number;
  conviction: number;
  drivers: string[];
  volRegime: string | null;
  correct: boolean;
  verdictVerb: string;
  entryIndex: number;
  exitIndex: number;
  series: ReplayPoint[];
}

// ── Research AI ─────────────────────────────────────────────────────────────
// Shapes returned by POST /api/research/query. Every answer arrives with the
// evidence behind it, so the UI can show what the answer was built from rather
// than asking the reader to take it on trust.

/** One cited piece of evidence: either an exact lookup or a retrieved passage. */
export interface ResearchSource {
  tag: string; // the [S1]/[E2] marker the answer text refers to
  kind: "structured" | "retrieved";
  artifact_id: string;
  artifact_type: string;
  title: string;
  source_path: string;
  heading?: string | null;
  chunk_id?: string | null;
  similarity?: number | null;
  snippet?: string | null;
}

/** A retrieved passage, shown in full in the evidence panel. */
export interface ResearchEvidence {
  chunk_id: string;
  artifact_id: string;
  artifact_type: string;
  title: string;
  heading?: string | null;
  source_path: string;
  similarity: number;
  retrieval_method: string;
  text: string;
}

export interface ResearchDriver {
  key: string;
  label: string;
  contribution: number;
  direction: "supports" | "opposes";
  featureValue: number;
}

/** The live signal the question was about, if it was about one. */
export interface ResearchSignalContext {
  ticker: string;
  company?: string;
  sector?: string;
  signal: SignalType;
  confidence: number;
  chanceLevel: number; // 33.3 — three classes, so this is the "no opinion" level
  expectedReturn5d?: number;
  risk?: string;
  model?: string;
  price?: number;
  change?: number;
  generatedAt?: string;
  drivers?: {
    supporting: ResearchDriver[];
    opposing: ResearchDriver[];
    asOf?: string;
  };
  riskControls?: {
    level?: string;
    sizingFactor?: number;
    inProposedBook?: boolean;
    proposedWeight?: number;
    limits?: Record<string, number | boolean>;
    note?: string;
  };
}

export interface ResearchAnswer {
  question: string;
  answer: string;
  intent: string;
  ticker: string | null;
  signal_context: ResearchSignalContext | null;
  sources: ResearchSource[];
  evidence: ResearchEvidence[];
  tool_calls: { tool: string; arguments: Record<string, unknown>; ok: boolean; note?: string }[];
  retrieval_trace: { step: string; detail: string; result_count: number }[];
  grounding_warnings: string[];
  grounded: boolean;
  llm: { provider: string; model: string; note?: string };
  latency_ms: number;
  over_latency_budget: boolean;
}

export interface ResearchHealth {
  status: string;
  indexReady: boolean;
  index: {
    chunks: number;
    artifacts: number;
    embedder: string;
    backend: string;
    byType: Record<string, number>;
    tickers: string[];
  };
  llm: { provider: string; mockMode: boolean; model: string | null; keyConfigured: boolean };
  embedding: { provider: string; active: string };
}

async function get<T>(path: string, init?: RequestInit, timeoutMs = API_TIMEOUT_MS): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
      signal: controller.signal,
    });
    if (!res.ok) throw new Error(`QuantML API ${path} -> ${res.status}`);
    return (await res.json()) as T;
  } finally {
    clearTimeout(timeoutId);
  }
}

export const api = {
  health: () => get<Record<string, unknown>>("/api/health"),
  metrics: () => get<unknown[]>("/api/metrics"),
  equity: (range?: number) =>
    get<MetricPoint[]>(`/api/equity${range ? `?range=${range}` : ""}`),
  signals: (type?: string) =>
    get<Signal[]>(`/api/signals${type ? `?type=${type}` : ""}`),
  models: () => get<{
    models: ModelRecord[];
    featureImportance: unknown[];
    experiments?: Array<{ id: string; model: string; metric: string; status: string; time: string }>;
    registry?: {
      championId: string | null;
      versions: Array<{
        id: string; version: string; name: string; status: string;
        metrics: { sharpe?: number; auc?: number; cagr?: number; maxDrawdown?: number };
        trainWindow: string; features?: number; dsr: number | null;
        gatePassed: boolean; promotedAt: string | null;
      }>;
    };
  }>("/api/models"),
  trades: () => get<Trade[]>("/api/trades"),
  replay: () => get<{ scenarios: ReplayScenario[] }>("/api/replay"),
  backtests: (config?: BacktestConfig) =>
    get<BacktestResult>("/api/backtests", {
      method: "POST",
      body: JSON.stringify(config ?? {}),
    }),
  risk: () => get<RiskSummary>("/api/risk"),
  validation: () => get<ValidationStudies>("/api/validation"),
  research: (prompt: string) =>
    get<RagResponse>("/api/research", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),

  // The grounded assistant. Needs the FastAPI backend — the Next.js route
  // handlers only serve the older /api/research shape.
  researchQuery: (body: {
    question: string;
    ticker?: string;
    model_version?: string;
    top_k?: number;
  }) =>
    get<ResearchAnswer>(
      "/api/research/query",
      { method: "POST", body: JSON.stringify(body) },
      // mock mode answers in milliseconds, but a real LLM needs room to think
      RESEARCH_TIMEOUT_MS,
    ),

  researchHealth: () => get<ResearchHealth>("/api/research/health"),

  researchExamples: () => get<{ examples: string[] }>("/api/research/examples"),
};
