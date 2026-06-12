import { NextResponse } from "next/server";
import { marketContext } from "@/lib/mock-data";

// GET /api/health - service + model status (mirrors FastAPI GET /health)
export function GET() {
  return NextResponse.json({
    status: "operational",
    time: new Date().toISOString(),
    market: marketContext.market,
    model: marketContext.model,
    universe: marketContext.universe,
    paperMode: marketContext.paperMode,
    version: "0.1.0",
  });
}
