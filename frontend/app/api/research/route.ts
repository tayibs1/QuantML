import { NextResponse } from "next/server";
import { getRagResponse } from "@/lib/mock-data";

// POST /api/research { prompt } — RAG explanation for a signal/question.
// Mirrors FastAPI POST /research. Swap getRagResponse for a real retrieval +
// LLM call (vector store + model) without changing the response shape.
export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const prompt = typeof body?.prompt === "string" ? body.prompt : "";
  if (!prompt.trim()) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }
  // Simulate retrieval + reasoning latency so the UI streaming state is visible.
  await new Promise((r) => setTimeout(r, 650));
  return NextResponse.json(getRagResponse(prompt));
}
