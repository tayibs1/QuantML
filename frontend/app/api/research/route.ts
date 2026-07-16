import { NextResponse } from "next/server";
import { explainSignal, buildContext } from "@/lib/signal-explainer";

// POST /api/research { prompt } - research explanation for a signal/question.
// Default: a free, no-key answer built from the model's own SHAP output.
// If GEMINI_API_KEY is set, it upgrades to a live LLM answer (Google Gemini
// free tier); on any error or over the rate limit it falls back to the free
// answer, so the demo always responds and never runs up a bill.

const MODEL = process.env.GEMINI_MODEL || "gemini-2.0-flash";
const MAX_PROMPT = 600;

const SYSTEM = `You are QuantML's research assistant. Explain why the model made a call, grounded strictly in the signal snapshot and model facts provided. Be concrete and quantitative and cite the SHAP drivers. This is a research tool, not financial advice — never tell the user to buy or sell. If a name isn't in the snapshot, say so and answer from the model's general behaviour.
Return ONLY a JSON object, no markdown, with exactly this shape:
{"answer": string, "sources": [{"title": string, "type": "Model report"|"Research"|"Earnings"|"News"|"Filing", "date": string, "snippet": string}], "signalContext": {"ticker": string, "signal": "BUY"|"HOLD"|"AVOID", "confidence": number, "model": string}, "riskWarnings": string[], "confidence": number}`;

// Basic in-memory rate limit so the optional LLM can't be abused: a few calls
// per IP per minute, plus a global hourly ceiling. Over either limit we serve
// the free answer instead of calling the model. (In-memory only: resets on cold
// start and isn't shared across serverless instances — enough for a demo.)
const PER_IP = 5;
const IP_WINDOW = 60_000;
const GLOBAL_MAX = 120;
const GLOBAL_WINDOW = 3_600_000;

const ipHits = new Map<string, number[]>();
let globalHits: number[] = [];

function ipOf(req: Request) {
  return req.headers.get("x-forwarded-for")?.split(",")[0].trim() || "unknown";
}

function overLimit(ip: string) {
  const now = Date.now();
  globalHits = globalHits.filter((t) => now - t < GLOBAL_WINDOW);
  if (globalHits.length >= GLOBAL_MAX) return true;
  const hits = (ipHits.get(ip) ?? []).filter((t) => now - t < IP_WINDOW);
  if (hits.length >= PER_IP) {
    ipHits.set(ip, hits);
    return true;
  }
  hits.push(now);
  ipHits.set(ip, hits);
  globalHits.push(now);
  if (ipHits.size > 5000) ipHits.clear(); // keep the map from growing unbounded
  return false;
}

async function callGemini(key: string, prompt: string) {
  const res = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${MODEL}:generateContent`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "x-goog-api-key": key },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: `${SYSTEM}\n\n---\n${buildContext()}` }] },
      contents: [{ role: "user", parts: [{ text: prompt }] }],
      generationConfig: { responseMimeType: "application/json", maxOutputTokens: 1500, temperature: 0.4 },
    }),
  });
  if (!res.ok) throw new Error(`gemini ${res.status}`);
  const data = await res.json();
  const text: string | undefined = data?.candidates?.[0]?.content?.parts?.[0]?.text;
  if (!text) throw new Error("gemini: empty response");
  return JSON.parse(text);
}

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const prompt = typeof body?.prompt === "string" ? body.prompt.slice(0, MAX_PROMPT) : "";
  if (!prompt.trim()) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }

  // Free, no-key answer from the model's own output — always available.
  const base = explainSignal(prompt);

  const key = process.env.GEMINI_API_KEY || process.env.GOOGLE_API_KEY;
  if (!key || overLimit(ipOf(request))) {
    return NextResponse.json(base);
  }

  try {
    const llm = await callGemini(key, prompt);
    return NextResponse.json({ prompt, ...llm });
  } catch {
    return NextResponse.json(base);
  }
}
