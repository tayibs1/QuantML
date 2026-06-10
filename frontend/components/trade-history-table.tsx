"use client";

import { motion } from "motion/react";
import { Badge } from "./ui/badge";
import { trades as mockTrades, type Trade } from "@/lib/mock-data";
import { cn, formatSignedPct } from "@/lib/utils";

export function TradeHistoryTable({ data = mockTrades }: { data?: Trade[] }) {
  return (
    <div className="overflow-x-auto no-scrollbar">
      <table className="w-full min-w-[640px] border-collapse text-sm">
        <thead>
          <tr className="border-b border-white/8 text-left">
            {["ID", "Date", "Ticker", "Side", "Entry", "Exit", "Return", "P&L", "Hold"].map(
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
          {data.map((t, i) => (
            <motion.tr
              key={t.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.03 }}
              className="border-b border-white/5 transition-colors hover:bg-white/[0.02]"
            >
              <td className="px-3 py-2.5 font-mono text-[11px] text-slate-500">
                {t.id}
              </td>
              <td className="px-3 py-2.5 font-mono text-[11px] text-slate-400">
                {t.date}
              </td>
              <td className="px-3 py-2.5 font-semibold text-white">{t.ticker}</td>
              <td className="px-3 py-2.5">
                <Badge variant={t.side === "LONG" ? "bull" : "bear"}>
                  {t.side}
                </Badge>
              </td>
              <td className="px-3 py-2.5 font-mono text-xs text-slate-300 data">
                ${t.entry.toFixed(2)}
              </td>
              <td className="px-3 py-2.5 font-mono text-xs text-slate-300 data">
                ${t.exit.toFixed(2)}
              </td>
              <td
                className={cn(
                  "px-3 py-2.5 font-mono text-xs data",
                  t.ret >= 0 ? "text-bull-soft" : "text-bear-soft"
                )}
              >
                {formatSignedPct(t.ret, 2)}
              </td>
              <td
                className={cn(
                  "px-3 py-2.5 font-mono text-xs data",
                  t.pnl >= 0 ? "text-bull-soft" : "text-bear-soft"
                )}
              >
                {t.pnl >= 0 ? "+" : "-"}${Math.abs(t.pnl).toLocaleString()}
              </td>
              <td className="px-3 py-2.5 font-mono text-[11px] text-slate-400">
                {t.hold}d
              </td>
            </motion.tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
