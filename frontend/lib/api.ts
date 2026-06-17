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

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

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
};
