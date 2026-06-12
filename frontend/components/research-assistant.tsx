"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import {
  ArrowUp,
  Bot,
  FileText,
  Newspaper,
  ScrollText,
  Sparkles,
  TrendingUp,
  AlertTriangle,
  ShieldCheck,
  Loader2,
  type LucideIcon,
} from "lucide-react";
import { GlassPanel } from "./glass-panel";
import { Badge } from "./ui/badge";
import {
  examplePrompts,
  getRagResponse,
  type RagResponse,
  type RagSource,
} from "@/lib/mock-data";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

type Message =
  | { role: "user"; text: string; id: number }
  | { role: "assistant"; data: RagResponse; id: number };

const SOURCE_ICON: Record<RagSource["type"], LucideIcon> = {
  Filing: FileText,
  News: Newspaper,
  "Model report": ScrollText,
  Earnings: ScrollText,
  Research: ScrollText,
};

export function ResearchAssistant({
  compact = false,
  initialPrompt,
}: {
  compact?: boolean;
  initialPrompt?: string;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const idRef = useRef(0);

  const send = async (text: string) => {
    const q = text.trim();
    if (!q || thinking) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q, id: idRef.current++ }]);
    setThinking(true);
    try {
      // real round trip: client -> /api/research route (or FastAPI when
      // NEXT_PUBLIC_API_URL is set) -> JSON -> render
      const data = await api.research(q);
      setMessages((m) => [...m, { role: "assistant", data, id: idRef.current++ }]);
    } catch {
      // if the API can't be reached, fall back so the demo still works
      setMessages((m) => [
        ...m,
        { role: "assistant", data: getRagResponse(q), id: idRef.current++ },
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
      className={cn("flex flex-col overflow-hidden", compact ? "h-[560px]" : "h-[640px]")}
    >
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-white/6 px-4 py-3">
        <span className="relative grid size-9 place-items-center rounded-xl border border-brand-400/30 bg-brand-500/10">
          <Bot className="size-5 text-brand-300" />
          <span className="absolute -right-0.5 -top-0.5 size-2.5 rounded-full border-2 border-ink-850 bg-bull" />
        </span>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-white">Research AI</h3>
            <Badge variant="brand" className="px-1.5 py-0 text-[9px]">
              RAG
            </Badge>
          </div>
          <p className="font-mono text-[10px] text-slate-500">
            Explains signals · does not place trades
          </p>
        </div>
        <span className="hidden items-center gap-1 font-mono text-[10px] text-slate-500 sm:flex">
          <span className="size-1.5 rounded-full bg-bull" /> connected
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
              Ask about any signal or position
            </p>
            <p className="mt-1 max-w-xs text-xs text-slate-500">
              Grounded in filings, news, earnings and model reports.
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
          )
        )}

        {thinking && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center gap-2 text-xs text-slate-500"
          >
            <Loader2 className="size-3.5 animate-spin text-brand-300" />
            Retrieving sources & reasoning…
          </motion.div>
        )}
      </div>

      {/* Suggested prompts */}
      {messages.length === 0 && (
        <div className="border-t border-white/6 px-4 py-3">
          <div className="flex flex-wrap gap-1.5">
            {examplePrompts.slice(0, compact ? 3 : 5).map((p) => (
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
            placeholder="Ask the research assistant…"
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
      </form>
    </GlassPanel>
  );
}

function AssistantMessage({ data }: { data: RagResponse }) {
  const ctxTone =
    data.signalContext.signal === "BUY"
      ? "bull"
      : data.signalContext.signal === "AVOID"
        ? "bear"
        : "hold";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-3"
    >
      {/* Answer */}
      <div className="rounded-2xl rounded-tl-sm border border-white/8 bg-white/[0.02] p-3.5">
        <div className="mb-2 flex items-center gap-1.5">
          <Bot className="size-3.5 text-brand-300" />
          <span className="font-mono text-[10px] uppercase tracking-wider text-brand-300/80">
            Answer
          </span>
        </div>
        <p className="text-sm leading-relaxed text-slate-200">{data.answer}</p>
      </div>

      {/* Signal context */}
      <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
        <TrendingUp className="size-3.5 text-slate-400" />
        <span className="text-xs text-slate-400">Signal context</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="font-mono text-xs font-medium text-white">
            {data.signalContext.ticker}
          </span>
          <Badge variant={ctxTone as "bull" | "bear" | "hold"}>
            {data.signalContext.signal}
          </Badge>
          <span className="font-mono text-xs text-slate-400">
            {data.signalContext.confidence}%
          </span>
        </span>
      </div>

      {/* Sources */}
      <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
        <div className="mb-2 flex items-center gap-1.5">
          <FileText className="size-3.5 text-violet-glow" />
          <span className="font-mono text-[10px] uppercase tracking-wider text-violet-200/80">
            Retrieved sources · {data.sources.length}
          </span>
        </div>
        <div className="space-y-2">
          {data.sources.map((src, i) => {
            const Icon = SOURCE_ICON[src.type];
            return (
              <div
                key={i}
                className="flex gap-2.5 rounded-lg border border-white/6 bg-white/[0.015] p-2.5"
              >
                <Icon className="mt-0.5 size-3.5 shrink-0 text-slate-500" />
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-xs font-medium text-slate-200">
                      {src.title}
                    </span>
                    <span className="ml-auto shrink-0 font-mono text-[9px] text-slate-600">
                      {src.date}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-1.5">
                    <Badge variant="outline" className="px-1.5 py-0 text-[9px]">
                      {src.type}
                    </Badge>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-slate-500">
                    {src.snippet}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Risk warnings */}
      <div className="rounded-xl border border-hold/25 bg-hold/[0.05] p-3">
        <div className="mb-2 flex items-center gap-1.5">
          <AlertTriangle className="size-3.5 text-hold-soft" />
          <span className="font-mono text-[10px] uppercase tracking-wider text-hold-soft/90">
            Risk warnings
          </span>
        </div>
        <ul className="space-y-1.5">
          {data.riskWarnings.map((w, i) => (
            <li key={i} className="flex gap-2 text-xs text-slate-300">
              <span className="mt-1.5 size-1 shrink-0 rounded-full bg-hold" />
              {w}
            </li>
          ))}
        </ul>
      </div>

      {/* Confidence + disclaimer */}
      <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2">
        <ShieldCheck className="size-3.5 text-brand-300" />
        <span className="text-xs text-slate-400">Interpretation confidence</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="h-1.5 w-20 overflow-hidden rounded-full bg-white/8">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${data.confidence}%` }}
              transition={{ duration: 0.9, ease: "easeOut" }}
              className="h-full rounded-full bg-brand-400"
            />
          </div>
          <span className="font-mono text-xs font-medium text-brand-200">
            {data.confidence}%
          </span>
        </div>
      </div>
    </motion.div>
  );
}
