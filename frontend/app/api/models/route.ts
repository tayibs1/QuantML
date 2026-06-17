import { NextResponse } from "next/server";
import { featureImportance, models, modelRegistry } from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/models.json";

// GET /api/models - real model registry + feature importance (champion + baselines).
const real = snapshot as { models?: unknown[] };

export function GET() {
  if (Array.isArray(real.models) && real.models.length) {
    return NextResponse.json(snapshot);
  }
  return NextResponse.json({ models, featureImportance, registry: modelRegistry });
}
