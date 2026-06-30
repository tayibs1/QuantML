import { NextResponse } from "next/server";
import snapshot from "@/lib/snapshot/replay.json";

// GET /api/replay - real backtest trades replayed: the model's entry, the daily price
// path it played out over, and the realized P&L at exit.
export function GET() {
  return NextResponse.json(snapshot);
}
