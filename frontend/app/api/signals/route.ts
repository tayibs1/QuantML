import { NextResponse } from "next/server";
import { signals } from "@/lib/mock-data";

// GET /api/signals?type=BUY — model-generated signals, optionally filtered
export function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");
  const data = type
    ? signals.filter((s) => s.signal === type.toUpperCase())
    : signals;
  return NextResponse.json(data);
}
