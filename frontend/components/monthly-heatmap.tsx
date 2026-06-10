"use client";

import { motion } from "motion/react";
import { monthlyReturns as mockMonthlyReturns } from "@/lib/mock-data";
import { cn } from "@/lib/utils";

type MonthlyRow = { year: number; months: (number | null)[] };

const MONTHS = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

function cellColor(v: number | null): string {
  if (v === null) return "bg-white/[0.015] text-transparent";
  const a = Math.min(Math.abs(v) / 8, 1);
  if (v >= 0)
    return `text-bull-soft`;
  return `text-bear-soft`;
}

function cellStyle(v: number | null): React.CSSProperties {
  if (v === null) return {};
  const a = Math.min(Math.abs(v) / 8, 1) * 0.55 + 0.05;
  return v >= 0
    ? { backgroundColor: `rgba(34,197,94,${a})` }
    : { backgroundColor: `rgba(244,63,94,${a})` };
}

export function MonthlyHeatmap({
  data = mockMonthlyReturns,
}: {
  data?: MonthlyRow[];
}) {
  const rows = data.length ? data : mockMonthlyReturns;
  return (
    <div className="overflow-x-auto no-scrollbar">
      <div className="min-w-[480px]">
        {/* Header */}
        <div className="mb-1 grid grid-cols-[40px_repeat(12,1fr)] gap-1">
          <div />
          {MONTHS.map((m, i) => (
            <div
              key={i}
              className="text-center font-mono text-[10px] text-slate-500"
            >
              {m}
            </div>
          ))}
        </div>
        {/* Rows */}
        <div className="space-y-1">
          {rows.map((row, ri) => (
            <div
              key={row.year}
              className="grid grid-cols-[40px_repeat(12,1fr)] gap-1"
            >
              <div className="flex items-center font-mono text-[10px] text-slate-500">
                {row.year}
              </div>
              {row.months.map((v, mi) => (
                <motion.div
                  key={mi}
                  initial={{ opacity: 0, scale: 0.8 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.25, delay: (ri * 12 + mi) * 0.006 }}
                  style={cellStyle(v)}
                  className={cn(
                    "group relative grid aspect-square place-items-center rounded-[5px] border border-white/5 font-mono text-[9px] font-medium transition-transform hover:z-10 hover:scale-110 hover:ring-1 hover:ring-white/20",
                    cellColor(v)
                  )}
                  title={v === null ? "" : `${row.year} · ${v > 0 ? "+" : ""}${v}%`}
                >
                  {v === null ? "" : Math.abs(v) >= 0.1 ? v.toFixed(0) : ""}
                </motion.div>
              ))}
            </div>
          ))}
        </div>
        {/* Legend */}
        <div className="mt-3 flex items-center justify-end gap-2 font-mono text-[10px] text-slate-500">
          <span>-8%</span>
          <div className="flex h-2.5 w-32 overflow-hidden rounded-full">
            <div className="flex-1 bg-bear/70" />
            <div className="flex-1 bg-bear/30" />
            <div className="flex-1 bg-white/10" />
            <div className="flex-1 bg-bull/30" />
            <div className="flex-1 bg-bull/70" />
          </div>
          <span>+8%</span>
        </div>
      </div>
    </div>
  );
}
