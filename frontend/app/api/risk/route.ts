import { NextResponse } from "next/server";
import {
  exposureByAsset,
  exposureBySector,
  positionRules,
  riskBudget,
  riskFlags,
  volatilityRegime,
} from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/risk.json";

// GET /api/risk - real risk snapshot (exposure, budget, regime, flags, rules) from the
// live proposed book. Falls back to seeded data if the snapshot is absent.
const real = snapshot as { flags?: unknown[] };

export function GET() {
  if (Array.isArray(real.flags)) {
    return NextResponse.json(snapshot);
  }
  return NextResponse.json({
    flags: riskFlags,
    budget: riskBudget,
    exposureByAsset,
    exposureBySector,
    volatilityRegime,
    positionRules,
  });
}
