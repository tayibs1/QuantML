"use client";

import type { TooltipProps } from "recharts";

export function ChartTooltip({
  active,
  payload,
  label,
  valueFormatter,
}: TooltipProps<number, string> & {
  valueFormatter?: (v: number, name: string) => string;
}) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-xl border border-white/10 bg-ink-850/95 px-3 py-2 text-xs shadow-panel backdrop-blur-md">
      {label != null && (
        <div className="mb-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-400">
          {label}
        </div>
      )}
      <div className="space-y-1">
        {payload.map((p, i) => (
          <div key={i} className="flex items-center gap-2">
            <span
              className="size-2 rounded-full"
              style={{ background: p.color as string }}
            />
            <span className="text-slate-400">{p.name}</span>
            <span className="ml-auto font-mono font-medium text-slate-100 data">
              {valueFormatter
                ? valueFormatter(p.value as number, p.name as string)
                : p.value}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
