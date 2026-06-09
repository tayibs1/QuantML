import { NextResponse } from "next/server";
import { dashboardMetrics } from "@/lib/mock-data";

// GET /api/metrics — top-level dashboard KPIs
export function GET() {
  return NextResponse.json(dashboardMetrics);
}
