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

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`QuantML API ${path} -> ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  health: () => get<Record<string, unknown>>("/api/health"),
  metrics: () => get<unknown[]>("/api/metrics"),
  equity: (range?: number) =>
    get<MetricPoint[]>(`/api/equity${range ? `?range=${range}` : ""}`),
  signals: (type?: string) =>
    get<Signal[]>(`/api/signals${type ? `?type=${type}` : ""}`),
  models: () => get<{ models: ModelRecord[]; featureImportance: unknown[] }>("/api/models"),
  trades: () => get<Trade[]>("/api/trades"),
  backtests: (config?: BacktestConfig) =>
    get<BacktestResult>("/api/backtests", {
      method: "POST",
      body: JSON.stringify(config ?? {}),
    }),
  risk: () => get<RiskSummary>("/api/risk"),
  research: (prompt: string) =>
    get<RagResponse>("/api/research", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};
