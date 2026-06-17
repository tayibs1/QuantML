import { NextResponse } from "next/server";
import snapshot from "@/lib/snapshot/validation.json";

// GET /api/validation - real robustness studies (rolling-window, training-window sweep,
// regime models, OOD, confidence, retrain cadence), snapshot of the live pipeline.
export function GET() {
  return NextResponse.json(snapshot);
}
