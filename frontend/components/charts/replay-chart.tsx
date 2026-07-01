"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import type { ReplayPoint } from "@/lib/api";

const axisStyle = {
  fontSize: 10,
  fontFamily: "var(--font-mono)",
  fill: "rgba(148,163,184,0.6)",
};

// Rebased-to-100 chart: the stock (accent, two-tone) races QQQ (dashed) from the
// signal date. The lookback is drawn muted; the outcome window grows as `revealed`
// advances.
export function ReplayChart({
  series,
  entryIndex,
  exitIndex,
  revealed,
  accent,
  height = 380,
}: {
  series: ReplayPoint[];
  entryIndex: number;
  exitIndex: number;
  revealed: number;
  accent: string;
  height?: number;
}) {
  const vals = series.flatMap((p) => [p.value, p.bench ?? p.value]);
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const pad = (max - min) * 0.1 || 1;

  const head = Math.min(revealed, series.length - 1);
  const entryDate = series[entryIndex]?.date;
  const exitDate = series[exitIndex]?.date;
  const showExit = revealed >= exitIndex;

  const data = series.map((p, i) => ({
    date: p.date,
    context: i <= entryIndex ? p.value : null,
    active: i >= entryIndex && i <= revealed ? p.value : null,
    bench: i <= revealed ? p.bench : null,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 12, right: 18, left: -6, bottom: 0 }}>
        <defs>
          <linearGradient id="replayFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.32} />
            <stop offset="100%" stopColor={accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
        <XAxis
          dataKey="date"
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          minTickGap={44}
          tickFormatter={(v: string) => v.slice(5)}
        />
        <YAxis
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          width={44}
          domain={[min - pad, max + pad]}
          tickFormatter={(v: number) => v.toFixed(0)}
        />
        <ReferenceLine y={100} stroke="rgba(255,255,255,0.14)" strokeDasharray="2 4" />
        <ReferenceLine
          x={entryDate}
          stroke={accent}
          strokeDasharray="4 3"
          strokeOpacity={0.7}
          label={{ value: "SIGNAL", position: "insideTopLeft", fill: accent, fontSize: 10, fontWeight: 700 }}
        />
        {showExit && (
          <ReferenceLine
            x={exitDate}
            stroke="rgba(148,163,184,0.5)"
            strokeDasharray="4 3"
            label={{ value: "EXIT", position: "insideTopRight", fill: "rgba(148,163,184,0.7)", fontSize: 10, fontWeight: 700 }}
          />
        )}
        <Line
          type="monotone"
          dataKey="bench"
          name="QQQ"
          stroke="#a78bfa"
          strokeWidth={1.5}
          strokeDasharray="4 3"
          dot={false}
          isAnimationActive={false}
          connectNulls
        />
        <Area
          type="monotone"
          dataKey="context"
          stroke="rgba(148,163,184,0.5)"
          strokeWidth={1.5}
          fill="none"
          dot={false}
          isAnimationActive={false}
          connectNulls
        />
        <Area
          type="monotone"
          dataKey="active"
          stroke={accent}
          strokeWidth={2.5}
          fill="url(#replayFill)"
          dot={false}
          activeDot={false}
          isAnimationActive={false}
          connectNulls
        />
        {series[head] && (
          <ReferenceDot
            x={series[head].date}
            y={series[head].value}
            r={4.5}
            fill={accent}
            stroke="#04060c"
            strokeWidth={2}
            isFront
          />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  );
}
