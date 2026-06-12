import { NextResponse } from "next/server";
import { trades } from "@/lib/mock-data";

// GET /api/trades - closed trade history from the latest backtest
export function GET() {
  return NextResponse.json(trades);
}
