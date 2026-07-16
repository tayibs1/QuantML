import { NextResponse } from "next/server";
import Anthropic from "@anthropic-ai/sdk";
import { getRagResponse } from "@/lib/mock-data";
import signalsSnapshot from "@/lib/snapshot/signals.json";
import modelsSnapshot from "@/lib/snapshot/models.json";
import metricsSnapshot from "@/lib/snapshot/metrics.json";

// POST /api/research { prompt } - RAG explanation for a signal/question.
// With ANTHROPIC_API_KEY set, Claude answers grounded in the current signal
// snapshot; without a key (or on any error) it falls back to the canned
// response so the demo still works.

const MODEL = "claude-opus-4-8";
const MAX_PROMPT = 600;

type Signal = {
  ticker: string;
  company: string;
  signal: string;
  confidence: number;
  expectedReturn5d: number;
  risk: string;
  model: string;
  drivers: string[];
  sector: string;
};

// The JSON Claude must return — matches the RagResponse the UI renders.
const schema = {
  type: "object",
  additionalProperties: false,
  required: ["answer", "sources", "signalContext", "riskWarnings", "confidence"],
  properties: {
    answer: { type: "string" },
    sources: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["title", "type", "date", "snippet"],
        properties: {
          title: { type: "string" },
          type: { type: "string" },
          date: { type: "string" },
          snippet: { type: "string" },
        },
      },
    },
    signalContext: {
      type: "object",
      additionalProperties: false,
      required: ["ticker", "signal", "confidence", "model"],
      properties: {
        ticker: { type: "string" },
        signal: { type: "string", enum: ["BUY", "HOLD", "AVOID"] },
        confidence: { type: "number" },
        model: { type: "string" },
      },
    },
    riskWarnings: { type: "array", items: { type: "string" } },
    confidence: { type: "number" },
  },
} as const;

function buildContext() {
  const signals = signalsSnapshot as Signal[];
  const rows = signals
    .map(
      (s) =>
        `${s.ticker} (${s.company}, ${s.sector}) — ${s.signal} @ ${s.confidence}% conf, E[5d] ${s.expectedReturn5d}%, ${s.risk} risk. Drivers: ${s.drivers.join(", ")}`
    )
    .join("\n");
  const model = (modelsSnapshot as { models: Record<string, unknown>[] }).models?.[0] ?? {};
  const feats = ((modelsSnapshot as { featureImportance?: { feature: string; importance: number }[] }).featureImportance ?? [])
    .slice(0, 8)
    .map((f) => `${f.feature} (${(f.importance * 100).toFixed(1)}%)`)
    .join(", ");
  const kpis = (metricsSnapshot as { label: string; value: number; suffix: string }[])
    .map((m) => `${m.label}: ${m.value}${m.suffix}`)
    .join(" · ");

  return `MODEL\n${JSON.stringify(model)}\n\nTOP FEATURES (SHAP importance)\n${feats}\n\nBACKTEST KPIs\n${kpis}\n\nCURRENT SIGNALS\n${rows}`;
}

const SYSTEM = `You are QuantML's research assistant. Explain why the model made a call, grounded strictly in the signal snapshot and model facts provided. Be concrete and quantitative and cite the SHAP drivers behind the call. This is a research tool, not financial advice, so never tell the user to buy or sell. If a name isn't in the snapshot, say so and answer from the model's general behaviour. Return JSON matching the schema: a clear answer, 2-3 plausible sources (earnings, sell-side research, or the model's SHAP report), the signalContext for the name in question, honest riskWarnings, and an overall confidence 0-100.`;

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const prompt = typeof body?.prompt === "string" ? body.prompt.slice(0, MAX_PROMPT) : "";
  if (!prompt.trim()) {
    return NextResponse.json({ error: "prompt is required" }, { status: 400 });
  }

  const mock = getRagResponse(prompt);
  if (!process.env.ANTHROPIC_API_KEY) {
    return NextResponse.json(mock);
  }

  try {
    const client = new Anthropic();
    const res = await client.messages.create({
      model: MODEL,
      max_tokens: 1500,
      system: [
        { type: "text", text: `${SYSTEM}\n\n---\n${buildContext()}`, cache_control: { type: "ephemeral" } },
      ],
      output_config: { format: { type: "json_schema", schema } },
      messages: [{ role: "user", content: prompt }],
    } as Anthropic.MessageCreateParamsNonStreaming);

    const text = res.content.find((b) => b.type === "text");
    if (!text || text.type !== "text") return NextResponse.json(mock);
    const parsed = JSON.parse(text.text);
    return NextResponse.json({ prompt, ...parsed });
  } catch {
    // key present but the call failed — keep the demo working
    return NextResponse.json(mock);
  }
}
