import { NextResponse } from "next/server";
import {
  backtestMetrics,
  equitySeries,
  monthlyReturns,
  trades,
} from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/backtests.json";

// POST /api/backtests - returns the real cost-aware walk-forward backtest result
// (snapshot of the live engine). Falls back to a seeded result if the snapshot is absent.
const real = snapshot as { equity?: unknown[] };

export async function POST(req: Request) {
  const cfg = await req.json().catch(() => ({}));

  if (Array.isArray(real.equity) && real.equity.length) {
    return NextResponse.json({ ...snapshot, config: cfg });
  }

  const last = equitySeries[equitySeries.length - 1];
  return NextResponse.json({
    source: "mock",
    config: cfg,
    window: { start: equitySeries[0].date, end: last.date, rebalances: equitySeries.length },
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
