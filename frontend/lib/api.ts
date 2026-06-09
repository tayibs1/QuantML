/**
 * QuantML API client.
 *
 * By default this calls the Next.js route handlers in `app/api/*` (same origin),
 * so the app is genuinely fetching its data over HTTP end-to-end with no extra
 * process. Point it at the Python FastAPI backend by setting:
 *
 *     NEXT_PUBLIC_API_URL=http://localhost:8000
 *
 * The FastAPI endpoints in `backend/` return the exact same shapes, so nothing
 * else changes. See BACKEND.md for the full contract.
 */
import type {
  ModelRecord,
  RagResponse,
  RiskFlag,
  Signal,
  Trade,
  MetricPoint,
} from "./mock-data";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(`QuantML API ${path} → ${res.status}`);
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
  risk: () => get<{ flags: RiskFlag[]; [k: string]: unknown }>("/api/risk"),
  research: (prompt: string) =>
    get<RagResponse>("/api/research", {
      method: "POST",
      body: JSON.stringify({ prompt }),
    }),
};
