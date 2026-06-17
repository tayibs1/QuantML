import { NextResponse } from "next/server";
import { equitySeries, type MetricPoint } from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/equity.json";

// GET /api/equity?range=60 - real equity / benchmark / drawdown series from the backtest.
const real = snapshot as unknown as MetricPoint[];
const source: MetricPoint[] = real.length ? real : equitySeries;

export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const range = Number(searchParams.get("range") ?? 0);
  return NextResponse.json(range > 0 ? source.slice(-range) : source);
}
