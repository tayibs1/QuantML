import { NextResponse } from "next/server";
import { dashboardMetrics } from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/metrics.json";

// GET /api/metrics - real top-level dashboard KPIs from the latest backtest.
const real = snapshot as unknown[];

export function GET() {
  return NextResponse.json(real.length ? real : dashboardMetrics);
}
