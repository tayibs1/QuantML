"use client";

import Link from "next/link";
import { motion } from "motion/react";
import { ArrowUpRight } from "lucide-react";
import { Badge } from "./ui/badge";
import { signals as allSignals, type Signal } from "@/lib/mock-data";
import { cn, formatSignedPct } from "@/lib/utils";

const SIGNAL_VARIANT = {
  BUY: "bull",
  HOLD: "hold",
  AVOID: "bear",
} as const;

export function SignalsTable({
  data = allSignals,
  limit,
}: {
  data?: Signal[];
  limit?: number;
}) {
  const rows = limit ? data.slice(0, limit) : data;

  return (
    <div className="overflow-x-auto no-scrollbar">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-white/8 text-left">
            {["Ticker", "Signal", "Conf.", "Exp. 5D", "Risk", "Model", ""].map(
              (h) => (
                <th
                  key={h}
                  className="px-3 py-2.5 font-mono text-[10px] font-medium uppercase tracking-wider text-slate-500"
                >
                  {h}
                </th>
              )
            )}
          </tr>
        </thead>
        <tbody>
          {rows.map((s, i) => (
            <motion.tr
              key={s.ticker}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.04 }}
              className="group border-b border-white/5 transition-colors hover:bg-white/[0.02]"
            >
              <td className="px-3 py-3">
                <div className="flex flex-col">
                  <span className="font-semibold text-white">{s.ticker}</span>
                  <span className="font-mono text-[10px] text-slate-500">
                    ${s.price.toFixed(2)}
                  </span>
                </div>
              </td>
              <td className="px-3 py-3">
                <Badge variant={SIGNAL_VARIANT[s.signal]}>{s.signal}</Badge>
              </td>
              <td className="px-3 py-3">
                <div className="flex items-center gap-2">
                  <div className="h-1.5 w-12 overflow-hidden rounded-full bg-white/8">
                    <div
                      className="h-full rounded-full bg-brand-400"
                      style={{ width: `${s.confidence}%` }}
                    />
                  </div>
                  <span className="font-mono text-xs text-slate-300 data">
                    {s.confidence}%
                  </span>
                </div>
              </td>
              <td
                className={cn(
                  "px-3 py-3 font-mono text-xs data",
                  s.expectedReturn5d >= 0 ? "text-bull-soft" : "text-bear-soft"
                )}
              >
                {formatSignedPct(s.expectedReturn5d)}
              </td>
              <td className="px-3 py-3 text-xs text-slate-400">{s.risk}</td>
              <td className="px-3 py-3 font-mono text-[11px] text-slate-500">
                {s.model}
              </td>
              <td className="px-3 py-3 text-right">
                <Link
                  href={`/research?ticker=${s.ticker}`}
                  className="inline-flex items-center gap-1 text-xs text-brand-300 opacity-0 transition-opacity group-hover:opacity-100"
                >
                  Explain <ArrowUpRight className="size-3" />
                </Link>
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
