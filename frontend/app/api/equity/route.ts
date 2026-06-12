import { NextResponse } from "next/server";
import { equitySeries } from "@/lib/mock-data";

// GET /api/equity?range=60 - equity / benchmark / drawdown time series
export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const range = Number(searchParams.get("range") ?? 0);
  const data = range > 0 ? equitySeries.slice(-range) : equitySeries;
  return NextResponse.json(data);
}
