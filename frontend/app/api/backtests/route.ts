import { NextResponse } from "next/server";
import {
  backtestMetrics,
  equitySeries,
  monthlyReturns,
  trades,
} from "@/lib/mock-data";

// POST /api/backtests - mock fallback for when the FastAPI backend isn't running.
// The real engine (walk-forward, cost-aware) lives in backend/backtesting and
// returns the same shape; this just keeps the page working offline.
export async function POST(req: Request) {
  const cfg = await req.json().catch(() => ({}));
  const last = equitySeries[equitySeries.length - 1];
  return NextResponse.json({
    source: "mock",
    config: cfg,
    window: {
      start: equitySeries[0].date,
      end: last.date,
      rebalances: equitySeries.length,
    },
    metrics: {
      totalReturn: last.strategy / 100 - 1,
      benchTotalReturn: last.benchmark / 100 - 1,
    },
    summaryCards: backtestMetrics,
    equity: equitySeries,
    trades,
    tradeCount: trades.length,
    monthlyReturns,
  });
}
