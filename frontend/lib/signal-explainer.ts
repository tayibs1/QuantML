import signalsSnapshot from "@/lib/snapshot/signals.json";
import modelsSnapshot from "@/lib/snapshot/models.json";
import metricsSnapshot from "@/lib/snapshot/metrics.json";
import type { RagResponse } from "@/lib/mock-data";

// Free, no-key research answers built straight from the model's own output — the
// signal, conviction, SHAP drivers, expected return and risk for the name asked
// about. Also feeds the context for the optional LLM upgrade.

type Signal = {
  ticker: string;
  company: string;
  signal: "BUY" | "HOLD" | "AVOID";
  confidence: number;
  expectedReturn5d: number;
  risk: string;
  model: string;
  drivers: string[];
  sector: string;
};

const SIGNALS = signalsSnapshot as Signal[];
const MODEL = (modelsSnapshot as { models: Record<string, unknown>[] }).models?.[0] as
  | { name?: string; family?: string; features?: number; lastTrained?: string }
  | undefined;

const MODEL_NAME = MODEL?.name ?? "XGBoost-v3";
const MODEL_FAMILY = MODEL?.family ?? "gradient boosting";
const MODEL_FEATURES = MODEL?.features ?? 24;
const AS_OF = MODEL?.lastTrained ?? "2026-06-12";

function word(w: string) {
  return new RegExp(`(^|[^a-z0-9])${w.toLowerCase().replace(/[.*+?^${}()|[\]\\]/g, "")}([^a-z0-9]|$)`);
}

function findSignal(prompt: string): Signal | undefined {
  const q = prompt.toLowerCase();
  return (
    SIGNALS.find((s) => word(s.ticker).test(q)) ??
    SIGNALS.find((s) => q.includes(s.company.toLowerCase())) ??
    SIGNALS.find((s) => {
      const first = s.company.toLowerCase().split(/\s+/)[0];
      return first.length >= 4 && word(first).test(q);
    })
  );
}

function riskWarnings(s: Signal): string[] {
  const w: string[] = [];
  const r = s.risk.toLowerCase();
  if (r.includes("elevated") || r.includes("high")) {
    w.push(`${s.risk} risk — implied volatility is high, so size positions conservatively.`);
  }
  if (s.signal === "BUY") w.push("The call is momentum- and factor-driven; it can decay quickly on a regime shift.");
  if (s.signal === "AVOID") w.push("An AVOID is a relative call — the name can still rise in a broad market rally.");
  w.push("Model output for research only — not investment advice.");
  return w;
}

export function explainSignal(prompt: string): RagResponse {
  const s = findSignal(prompt);

  if (s) {
    const er = `${s.expectedReturn5d >= 0 ? "+" : ""}${s.expectedReturn5d.toFixed(2)}%`;
    const lead =
      s.signal === "BUY"
        ? "the setup favours continuation"
        : s.signal === "AVOID"
          ? "the factors are deteriorating relative to peers"
          : "there is no decisive edge either way";
    const [d0, d1, d2] = s.drivers;

    return {
      prompt,
      answer:
        `${MODEL_NAME} rates ${s.company} (${s.ticker}) a ${s.signal} at ${Math.round(s.confidence)}% conviction — ${lead}. ` +
        `The call is led by ${d0}, ${d1} and ${d2}, the three features with the largest SHAP contribution for this name. ` +
        `It projects a ${er} five-day forward return in ${s.sector}, flagged as ${s.risk} risk.`,
      sources: [
        {
          title: `${MODEL_NAME} SHAP attribution — ${s.ticker}`,
          type: "Model report",
          date: AS_OF,
          snippet: `Top contributors: ${s.drivers.join(", ")}. Predicted 5-day return ${er}.`,
        },
        {
          title: `${s.sector} factor screen`,
          type: "Research",
          date: AS_OF,
          snippet: `${s.ticker} scored ${s.signal} at ${Math.round(s.confidence)}% against the ${s.sector} cross-section; ${s.risk} risk bucket.`,
        },
      ],
      signalContext: { ticker: s.ticker, signal: s.signal, confidence: Math.round(s.confidence), model: MODEL_NAME },
      riskWarnings: riskWarnings(s),
      confidence: Math.round(s.confidence),
    };
  }

  const buys = SIGNALS.filter((x) => x.signal === "BUY")
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3)
    .map((b) => `${b.ticker} (${Math.round(b.confidence)}%)`)
    .join(", ");

  return {
    prompt,
    answer:
      `That name isn't in the current NASDAQ-100 signal snapshot, so there's no specific call to attribute. ` +
      `Right now the model's highest-conviction BUYs are ${buys}. ` +
      `In general, ${MODEL_NAME} (${MODEL_FAMILY}) scores every name from ${MODEL_FEATURES} features — momentum, volatility, mean-reversion and volume — and issues BUY / HOLD / AVOID with SHAP-ranked drivers behind each call.`,
    sources: [
      {
        title: `${MODEL_NAME} methodology`,
        type: "Model report",
        date: AS_OF,
        snippet: `Walk-forward ${MODEL_FAMILY} classifier; ${MODEL_FEATURES} features; SHAP attribution per signal.`,
      },
    ],
    signalContext: { ticker: "—", signal: "HOLD", confidence: 41, model: MODEL_NAME },
    riskWarnings: ["Model output for research only — not investment advice."],
    confidence: 40,
  };
}

// Compact grounding passed to the optional LLM.
export function buildContext(): string {
  const rows = SIGNALS.map(
    (s) =>
      `${s.ticker} (${s.company}, ${s.sector}) — ${s.signal} @ ${s.confidence}% conf, E[5d] ${s.expectedReturn5d}%, ${s.risk} risk. Drivers: ${s.drivers.join(", ")}`
  ).join("\n");
  const feats = ((modelsSnapshot as { featureImportance?: { feature: string; importance: number }[] }).featureImportance ?? [])
    .slice(0, 8)
    .map((f) => `${f.feature} (${(f.importance * 100).toFixed(1)}%)`)
    .join(", ");
  const kpis = (metricsSnapshot as { label: string; value: number; suffix: string }[])
    .map((m) => `${m.label}: ${m.value}${m.suffix}`)
    .join(" · ");
  return `MODEL\n${JSON.stringify(MODEL ?? {})}\n\nTOP FEATURES (SHAP importance)\n${feats}\n\nBACKTEST KPIs\n${kpis}\n\nCURRENT SIGNALS\n${rows}`;
}
