import { NextResponse } from "next/server";
import {
  exposureByAsset,
  exposureBySector,
  positionRules,
  riskBudget,
  riskFlags,
  volatilityRegime,
} from "@/lib/mock-data";

// GET /api/risk - full risk snapshot (exposure, budget, regime, flags, rules)
export function GET() {
  return NextResponse.json({
    flags: riskFlags,
    budget: riskBudget,
    exposureByAsset,
    exposureBySector,
    volatilityRegime,
    positionRules,
  });
}
