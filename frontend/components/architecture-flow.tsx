"use client";

import { motion } from "motion/react";
import {
  Database,
  SlidersHorizontal,
  BrainCircuit,
  LineChart,
  ShieldAlert,
  LayoutDashboard,
  Bot,
} from "lucide-react";

const NODES = [
  { label: "Market Data", sub: "OHLCV · fundamentals", icon: Database },
  { label: "Feature Engine", sub: "technical · factor", icon: SlidersHorizontal },
  { label: "ML Signal Model", sub: "buy / hold / avoid", icon: BrainCircuit, key: true },
  { label: "Backtest Engine", sub: "walk-forward", icon: LineChart },
  { label: "Risk Layer", sub: "sizing · limits", icon: ShieldAlert },
  { label: "Dashboard", sub: "monitor · explain", icon: LayoutDashboard },
];

function Connector({ index }: { index: number }) {
  return (
    <div className="relative hidden h-px min-w-8 flex-1 self-center lg:block">
      <div className="absolute inset-0 bg-gradient-to-r from-white/10 via-white/15 to-white/10" />
      <motion.div
        className="absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full bg-brand-300"
        style={{ boxShadow: "0 0 8px rgba(45,212,191,0.9)" }}
        animate={{ left: ["0%", "100%"], opacity: [0, 1, 0] }}
        transition={{
          duration: 2,
          repeat: Infinity,
          ease: "easeInOut",
          delay: index * 0.35,
        }}
      />
    </div>
  );
}

function Node({
  node,
  index,
}: {
  node: (typeof NODES)[number];
  index: number;
}) {
  const Icon = node.icon;
  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.96 }}
      whileInView={{ opacity: 1, y: 0, scale: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.5, delay: index * 0.08 }}
      className="relative shrink-0"
    >
      <div
        className={`group relative flex w-36 flex-col items-center gap-2 rounded-2xl border p-4 text-center transition-colors ${
          node.key
            ? "border-brand-400/40 bg-brand-500/[0.08] shadow-glow"
            : "border-white/10 bg-white/[0.03] hover:border-white/20"
        }`}
      >
        <span
          className={`grid size-10 place-items-center rounded-xl border ${
            node.key
              ? "border-brand-400/40 bg-brand-500/15"
              : "border-white/10 bg-white/[0.04]"
          }`}
        >
          <Icon
            className={node.key ? "size-5 text-brand-300" : "size-5 text-slate-300"}
          />
        </span>
        <div>
          <div className="text-xs font-semibold text-white">{node.label}</div>
          <div className="mt-0.5 font-mono text-[9px] text-slate-500">{node.sub}</div>
        </div>
        {node.key && (
          <span className="absolute -inset-px -z-10 rounded-2xl bg-brand-500/10 blur-md" />
        )}
      </div>
    </motion.div>
  );
}

export function ArchitectureFlow() {
  return (
    <div className="relative">
      {/* Main pipeline */}
      <div className="mask-fade-x flex items-stretch gap-3 overflow-x-auto pb-4 lg:mask-none lg:justify-between lg:gap-0 lg:overflow-visible no-scrollbar">
        {NODES.map((node, i) => (
          <div key={node.label} className="flex items-stretch gap-3 lg:flex-1 lg:gap-0">
            <Node node={node} index={i} />
            {i < NODES.length - 1 && <Connector index={i} />}
          </div>
        ))}
      </div>

      {/* RAG branch */}
      <div className="mt-2 flex justify-center lg:mt-0">
        <div className="relative flex flex-col items-center">
          {/* vertical connector */}
          <div className="relative h-12 w-px">
            <div className="absolute inset-0 bg-gradient-to-b from-violet/40 to-violet/10" />
            <motion.div
              className="absolute left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-violet-glow"
              style={{ boxShadow: "0 0 8px rgba(167,139,250,0.9)" }}
              animate={{ top: ["0%", "100%"], opacity: [0, 1, 0] }}
              transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
            />
          </div>
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="flex w-64 items-center gap-3 rounded-2xl border border-violet/30 bg-violet/[0.07] p-4 shadow-glow-violet"
          >
            <span className="grid size-10 shrink-0 place-items-center rounded-xl border border-violet/40 bg-violet/15">
              <Bot className="size-5 text-violet-glow" />
            </span>
            <div className="text-left">
              <div className="text-xs font-semibold text-white">
                RAG Research Assistant
              </div>
              <div className="mt-0.5 font-mono text-[9px] text-slate-400">
                explains every signal with sources
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
