import { NextResponse } from "next/server";
import { signals as mockSignals, type Signal } from "@/lib/mock-data";
import snapshot from "@/lib/snapshot/signals.json";

// GET /api/signals?type=BUY - real model-generated signals (snapshot of the live
// pipeline), optionally filtered. Falls back to seeded data if the snapshot is absent.
const real = snapshot as unknown as Signal[];
const source: Signal[] = real.length ? real : mockSignals;

export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");
  const data = type ? source.filter((s) => s.signal === type.toUpperCase()) : source;
  return NextResponse.json(data);
}
