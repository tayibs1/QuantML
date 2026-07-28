"use client";

/**
 * The Research AI chat.
 *
 * Every answer is shown with the evidence behind it: the exact figures that were
 * looked up, the passages that were retrieved, and any warnings raised while
 * checking the answer against them. That is the point of the panel — an
 * explanation you can't trace back to a source is worth very little here, so the
 * source is always one click away.
 *
 * When the FastAPI backend isn't reachable it drops to the older /api/research
 * route, which still answers but without the evidence trail. The banner says
 * which mode is live rather than hiding the difference.
 */

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  AlertTriangle,
  ArrowUp,
  Bot,
  ChevronDown,
  Database,
  FileText,
  Loader2,
  Quote,
  ShieldCheck,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Wrench,
} from "lucide-react";
import { GlassPanel } from "./glass-panel";
import { Badge } from "./ui/badge";
import { api, type ResearchAnswer, type ResearchSource } from "@/lib/api";
import { getRagResponse } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type Message =
  | { role: "user"; text: string; id: number }
  | { role: "assistant"; data: ResearchAnswer; id: number };

const FALLBACK_EXAMPLES = [
  "Why did the model give NVDA its current signal?",
  "Which features drove the prediction for AMD?",
  "What does 20-day momentum mean?",
  "How did the model perform after transaction costs?",
  "What are the biggest limitations of this model?",
  "What would make this signal unreliable?",
];

/** Colour each artifact type consistently wherever it appears. */
const TYPE_TONE: Record<string, string> = {
  latest_signal: "border-brand-400/30 bg-brand-500/10 text-brand-200",
  shap_summary: "border-violet/30 bg-violet/10 text-violet-200",
  feature_dictionary: "border-sky-400/30 bg-sky-500/10 text-sky-200",
  validation_report: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  walk_forward_report: "border-emerald-400/30 bg-emerald-500/10 text-emerald-200",
  backtest_report: "border-amber-400/30 bg-amber-500/10 text-amber-200",
  risk_report: "border-hold/30 bg-hold/10 text-hold-soft",
  model_card: "border-slate-400/30 bg-slate-500/10 text-slate-200",
  structured_lookup: "border-brand-400/40 bg-brand-500/15 text-brand-100",
};

function typeTone(type: string) {
  return TYPE_TONE[type] ?? "border-white/10 bg-white/[0.03] text-slate-300";
}

function toneForSignal(signal: string) {
  return signal === "BUY" ? "bull" : signal === "AVOID" ? "bear" : "hold";
}

/** Render the answer's markdown-ish output: headings, bullets, bold. */
function AnswerBody({ text }: { text: string }) {
  const blocks = text.split("\n").filter((line) => line.trim().length > 0);
  return (
    <div className="space-y-1.5 text-sm leading-relaxed text-slate-200">
      {blocks.map((line, i) => {
        const heading = line.match(/^\*\*(.+?)\*\*$/);
        if (heading) {
          return (
            <p
              key={i}
              className="pt-2 font-mono text-[10px] uppercase tracking-wider text-brand-300/80"
            >
              {heading[1]}
            </p>
          );
        }
        const bullet = line.match(/^\s*-\s+(.*)$/);
        const content = bullet ? bullet[1] : line;
        // inline bold and the [S1]/[E2] citation tags
        const parts = content.split(/(\*\*[^*]+\*\*|\[[SE]\d+\])/g);
        const rendered = parts.map((part, j) => {
          if (/^\*\*[^*]+\*\*$/.test(part)) {
            return (
              <strong key={j} className="font-semibold text-white">
                {part.slice(2, -2)}
              </strong>
            );
          }
          if (/^\[[SE]\d+\]$/.test(part)) {
            return (
              <span
                key={j}
                className="mx-0.5 rounded border border-brand-400/30 bg-brand-500/10 px-1 font-mono text-[9px] text-brand-200"
              >
                {part.slice(1, -1)}
              </span>
            );
          }
          return <span key={j}>{part}</span>;
        });
        return (
          <p key={i} className={cn("text-slate-300", bullet && "pl-4 -indent-2")}>
            {bullet && <span className="text-slate-600">• </span>}
            {rendered}
          </p>
        );
      })}
    </div>
  );
}

/** A collapsible section, used for the evidence and trace panels. */
function Collapsible({
  title,
  count,
  icon: Icon,
  children,
  defaultOpen = false,
}: {
  title: string;
  count?: number;
  icon: typeof FileText;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2.5 text-left"
      >
        <Icon className="size-3.5 text-slate-400" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400">
          {title}
          {count !== undefined && ` · ${count}`}
        </span>
        <ChevronDown
          className={cn(
            "ml-auto size-3.5 text-slate-500 transition-transform",
            open && "rotate-180",
          )}
        />
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="space-y-2 px-3 pb-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function SourceCard({ source }: { source: ResearchSource }) {
  return (
    <div className="rounded-lg border border-white/6 bg-white/[0.015] p-2.5">
      <div className="flex items-center gap-2">
        <span className="rounded border border-brand-400/30 bg-brand-500/10 px-1 font-mono text-[9px] text-brand-200">
          {source.tag}
        </span>
        <span className="truncate text-xs font-medium text-slate-200">
          {source.title}
        </span>
        {source.similarity != null && (
          <span className="ml-auto shrink-0 font-mono text-[9px] text-slate-500">
            {source.similarity.toFixed(3)}
          </span>
        )}
      </div>
      <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
        <span
          className={cn(
            "rounded border px-1.5 py-0 font-mono text-[9px]",
            typeTone(source.artifact_type),
          )}
        >
          {source.artifact_type}
        </span>
        <span className="truncate font-mono text-[9px] text-slate-600">
          {source.source_path}
        </span>
      </div>
      {source.chunk_id && (
        <div className="mt-1 font-mono text-[9px] text-slate-600">
          chunk {source.chunk_id}
        </div>
      )}
      {source.snippet && (
        <p className="mt-1.5 line-clamp-3 text-[11px] leading-relaxed text-slate-500">
          {source.snippet}
        </p>
      )}
    </div>
  );
}

function SignalContextPanel({ data }: { data: ResearchAnswer }) {
  const ctx = data.signal_context;
  if (!ctx) return null;
  const tone = toneForSignal(ctx.signal);
  const nearChance = ctx.confidence < ctx.chanceLevel + 8;

  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
      <div className="flex items-center gap-2">
        <TrendingUp className="size-3.5 text-slate-400" />
        <span className="font-mono text-[10px] uppercase tracking-wider text-slate-400">
          Signal context
        </span>
        <span className="ml-auto flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-white">{ctx.ticker}</span>
          <Badge variant={tone as "bull" | "bear" | "hold"}>{ctx.signal}</Badge>
        </span>
      </div>

      <div className="mt-2.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Confidence" value={`${ctx.confidence}%`} warn={nearChance} />
        <Stat label="Expected 5d" value={`${ctx.expectedReturn5d ?? "—"}%`} />
        <Stat label="Risk" value={ctx.risk ?? "—"} />
        <Stat label="Model" value={ctx.model ?? "—"} />
      </div>

      {nearChance && (
        <p className="mt-2 text-[11px] leading-relaxed text-hold-soft">
          Confidence is close to {ctx.chanceLevel}%, the level that means no
          opinion when there are three possible labels.
        </p>
      )}

      {ctx.drivers && (
        <div className="mt-3 space-y-1.5">
          {ctx.drivers.supporting.slice(0, 3).map((d) => (
            <DriverRow key={d.key} label={d.label} value={d.contribution} supports />
          ))}
          {ctx.drivers.opposing.slice(0, 2).map((d) => (
            <DriverRow key={d.key} label={d.label} value={d.contribution} />
          ))}
        </div>
      )}

      {ctx.riskControls?.note && (
        <p className="mt-2.5 border-t border-white/6 pt-2 text-[11px] leading-relaxed text-slate-500">
          {ctx.riskControls.note}
        </p>
      )}
    </div>
  );
}

function Stat({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-white/6 bg-white/[0.015] px-2 py-1.5">
      <div className="font-mono text-[9px] uppercase tracking-wider text-slate-600">
        {label}
      </div>
      <div className={cn("font-mono text-xs", warn ? "text-hold-soft" : "text-slate-200")}>
        {value}
      </div>
    </div>
  );
}

function DriverRow({
  label,
  value,
  supports,
}: {
  label: string;
  value: number;
  supports?: boolean;
}) {
  const Icon = supports ? TrendingUp : TrendingDown;
  return (
    <div className="flex items-center gap-2">
      <Icon className={cn("size-3 shrink-0", supports ? "text-bull" : "text-bear")} />
      <span className="truncate text-[11px] text-slate-300">{label}</span>
      <span
        className={cn(
          "ml-auto shrink-0 font-mono text-[10px]",
          supports ? "text-bull-soft" : "text-bear-soft",
        )}
      >
        {value > 0 ? "+" : ""}
        {value.toFixed(4)}
      </span>
    </div>
  );
}

function AssistantMessage({ data }: { data: ResearchAnswer }) {
  const structured = data.sources.filter((s) => s.kind === "structured");
  const retrieved = data.sources.filter((s) => s.kind === "retrieved");

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="space-y-3"
    >
      {/* Answer */}
      <div className="rounded-2xl rounded-tl-sm border border-white/8 bg-white/[0.02] p-3.5">
        <div className="mb-1 flex items-center gap-1.5">
          <Bot className="size-3.5 text-brand-300" />
          <span className="font-mono text-[10px] uppercase tracking-wider text-brand-300/80">
            Answer
          </span>
          <span className="ml-auto flex items-center gap-1.5">
            {!data.grounded && (
              <span className="rounded border border-hold/30 bg-hold/10 px-1.5 font-mono text-[9px] text-hold-soft">
                no evidence
              </span>
            )}
            <span className="font-mono text-[9px] text-slate-600">
              {data.llm.provider} · {data.latency_ms.toFixed(0)}ms
            </span>
          </span>
        </div>
        <AnswerBody text={data.answer} />
      </div>

      <SignalContextPanel data={data} />

      {/* Anything the grounding check flagged */}
      {data.grounding_warnings.length > 0 && (
        <div className="rounded-xl border border-hold/25 bg-hold/[0.05] p-3">
          <div className="mb-1.5 flex items-center gap-1.5">
            <AlertTriangle className="size-3.5 text-hold-soft" />
            <span className="font-mono text-[10px] uppercase tracking-wider text-hold-soft/90">
              Grounding checks
            </span>
          </div>
          <ul className="space-y-1.5">
            {data.grounding_warnings.map((w, i) => (
              <li key={i} className="flex gap-2 text-[11px] leading-relaxed text-slate-300">
                <span className="mt-1.5 size-1 shrink-0 rounded-full bg-hold" />
                {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      {structured.length > 0 && (
        <Collapsible title="Exact lookups" count={structured.length} icon={Wrench} defaultOpen>
          {structured.map((s) => (
            <SourceCard key={s.tag} source={s} />
          ))}
        </Collapsible>
      )}

      {retrieved.length > 0 && (
        <Collapsible title="Cited sources" count={retrieved.length} icon={FileText}>
          {retrieved.map((s) => (
            <SourceCard key={s.tag} source={s} />
          ))}
        </Collapsible>
      )}

      {data.evidence.length > 0 && (
        <Collapsible title="Retrieved evidence" count={data.evidence.length} icon={Quote}>
          {data.evidence.map((e) => (
            <div key={e.chunk_id} className="rounded-lg border border-white/6 bg-white/[0.015] p-2.5">
              <div className="flex items-center gap-2">
                <span
                  className={cn(
                    "rounded border px-1.5 font-mono text-[9px]",
                    typeTone(e.artifact_type),
                  )}
                >
                  {e.artifact_type}
                </span>
                <span className="truncate text-[11px] text-slate-300">
                  {e.heading ?? e.title}
                </span>
                <span className="ml-auto shrink-0 font-mono text-[9px] text-slate-600">
                  {e.similarity.toFixed(3)} · {e.retrieval_method}
                </span>
              </div>
              <p className="mt-1.5 line-clamp-6 whitespace-pre-wrap text-[11px] leading-relaxed text-slate-500">
                {e.text}
              </p>
            </div>
          ))}
        </Collapsible>
      )}

      {data.retrieval_trace.length > 0 && (
        <Collapsible title="Retrieval trace" count={data.retrieval_trace.length} icon={Database}>
          {data.retrieval_trace.map((step, i) => (
            <div key={i} className="flex gap-2 font-mono text-[10px]">
              <span className="shrink-0 text-brand-300/70">{step.step}</span>
              <span className="truncate text-slate-500">{step.detail}</span>
              <span className="ml-auto shrink-0 text-slate-600">{step.result_count}</span>
            </div>
          ))}
        </Collapsible>
      )}
    </motion.div>
  );
}

export function ResearchAI({
  compact = false,
  initialPrompt,
}: {
  compact?: boolean;
  initialPrompt?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [examples, setExamples] = useState<string[]>(FALLBACK_EXAMPLES);
  const [mode, setMode] = useState<"grounded" | "fallback" | "checking">("checking");
  const scrollRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);

  // Find out up front whether the grounded backend is reachable, so the header
  // can be honest about which mode the answers are coming from.
  useEffect(() => {
    let cancelled = false;
    api
      .researchHealth()
      .then((h) => {
        if (cancelled) return;
        setMode(h.indexReady ? "grounded" : "fallback");
      })
      .catch(() => !cancelled && setMode("fallback"));
    api
      .researchExamples()
      .then((r) => !cancelled && r.examples?.length && setExamples(r.examples))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const send = async (text: string) => {
    const question = text.trim();
    if (!question || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: question, id: idRef.current++ }]);
    setThinking(true);

    try {
      const data = await api.researchQuery({ question });
      setMessages((m) => [...m, { role: "assistant", data, id: idRef.current++ }]);
      setMode("grounded");
    } catch {
      // No backend: fall back to the older shape so the demo still answers,
      // and reshape it into what this component renders.
      const legacy = await api.research(question).catch(() => getRagResponse(question));
      setMode("fallback");
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          id: idRef.current++,
          data: {
            question,
            answer: legacy.answer,
            intent: "fallback",
            ticker: legacy.signalContext.ticker,
            signal_context: {
              ticker: legacy.signalContext.ticker,
              signal: legacy.signalContext.signal,
              confidence: legacy.signalContext.confidence,
              chanceLevel: 33.3,
              model: legacy.signalContext.model,
            },
            sources: [],
            evidence: [],
            tool_calls: [],
            retrieval_trace: [],
            grounding_warnings: [
              "Answered without the retrieval backend, so this response has no cited artifacts.",
              ...legacy.riskWarnings,
            ],
            grounded: false,
            llm: { provider: "fallback", model: "" },
            latency_ms: 0,
            over_latency_budget: false,
          },
        },
      ]);
    } finally {
      setThinking(false);
    }
  };

  useEffect(() => {
    if (initialPrompt) send(initialPrompt);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPrompt]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, thinking]);

  return (
    <GlassPanel
      strong
      className={cn("flex flex-col overflow-hidden", compact ? "h-[560px]" : "h-[720px]")}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-white/6 px-4 py-3">
        <span className="relative grid size-9 place-items-center rounded-xl border border-brand-400/30 bg-brand-500/10">
          <Bot className="size-5 text-brand-300" />
          <span
            className={cn(
              "absolute -right-0.5 -top-0.5 size-2.5 rounded-full border-2 border-ink-850",
              mode === "grounded" ? "bg-bull" : mode === "checking" ? "bg-slate-500" : "bg-hold",
            )}
          />
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">Research AI</h3>
            <Badge variant="brand" className="px-1.5 py-0 text-[9px]">
              Grounded RAG
            </Badge>
          </div>
          <p className="font-mono text-[10px] text-slate-500">
            Explains QuantML signals · cites artifacts · not advice
          </p>
        </div>
        <span className="hidden items-center gap-1 font-mono text-[10px] text-slate-500 sm:flex">
          <span
            className={cn(
              "size-1.5 rounded-full",
              mode === "grounded" ? "bg-bull" : mode === "checking" ? "bg-slate-500" : "bg-hold",
            )}
          />
          {/* don't claim a mode before the health check has answered */}
          {mode === "grounded"
            ? "artifact index live"
            : mode === "checking"
              ? "connecting…"
              : "snapshot fallback"}
        </span>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-4 no-scrollbar">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <span className="grid size-12 place-items-center rounded-2xl border border-brand-400/20 bg-brand-500/10">
              <Sparkles className="size-6 text-brand-300" />
            </span>
            <p className="mt-4 text-sm font-medium text-slate-200">
              Ask why a signal fired, or what would break it
            </p>
            <p className="mt-1 max-w-sm text-xs leading-relaxed text-slate-500">
              Answers come from QuantML&apos;s own artifacts — live signals, feature
              attribution, validation studies, backtests and the risk framework.
              Missing evidence is reported, not guessed.
            </p>
          </div>
        )}

        {messages.map((m) =>
          m.role === "user" ? (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-end"
            >
              <div className="max-w-[85%] rounded-2xl rounded-br-sm border border-brand-400/25 bg-brand-500/10 px-3.5 py-2 text-sm text-slate-100">
                {m.text}
              </div>
            </motion.div>
          ) : (
            <AssistantMessage key={m.id} data={m.data} />
          ),
        )}

        {thinking && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-xs text-slate-500"
          >
            <Loader2 className="size-3.5 animate-spin text-brand-300" />
            Looking up exact figures and searching artifacts…
          </motion.div>
        )}
      </div>

      {/* Suggested questions */}
      {messages.length === 0 && (
        <div className="border-t border-white/6 px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {examples.slice(0, compact ? 3 : 6).map((p) => (
              <button
                key={p}
                onClick={() => send(p)}
                className="rounded-lg border border-white/8 bg-white/[0.02] px-2.5 py-1.5 text-left text-[11px] text-slate-300 transition-colors hover:border-brand-400/30 hover:bg-brand-500/[0.06] hover:text-brand-100"
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Composer */}
      <form
        onSubmit={(e) => {
          e.preventDefault();
          send(input);
        }}
        className="border-t border-white/6 p-3"
      >
        <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2 focus-within:border-brand-400/40 focus-within:ring-1 focus-within:ring-brand-400/20">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about a signal, a feature, the validation or the risks…"
            className="flex-1 bg-transparent text-sm text-slate-100 placeholder:text-slate-600 focus:outline-none"
          />
          <button
            type="submit"
            disabled={!input.trim() || thinking}
            className="grid size-7 shrink-0 place-items-center rounded-lg bg-brand-500 text-ink-950 transition-all hover:bg-brand-400 disabled:opacity-40"
          >
            <ArrowUp className="size-4" />
          </button>
        </div>
        <p className="mt-2 flex items-center gap-1.5 text-[10px] text-slate-600">
          <ShieldCheck className="size-3" />
          Model-generated research explanations, not investment advice.
        </p>
      </form>
    </GlassPanel>
  );
}
