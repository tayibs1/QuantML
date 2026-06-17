import { NextResponse } from "next/server";
import { trades as mockTrades, type Trade } from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/trades.json";

// GET /api/trades - real closed-trade history from the latest backtest.
const real = snapshot as unknown as Trade[];

export function GET() {
  return NextResponse.json(real.length ? real : mockTrades);
}
