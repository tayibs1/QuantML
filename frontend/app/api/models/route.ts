import { NextResponse } from "next/server";
import { featureImportance, models, modelRegistry } from "@/lib/mock-data";

// GET /api/models - model registry + feature importance
export function GET() {
  return NextResponse.json({ models, featureImportance, registry: modelRegistry });
}
