"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
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

// Two-tone area: the lookback context is drawn muted and complete; the trade window
// (entry -> revealed) is drawn in the outcome colour and grows as `revealed` advances.
export function ReplayChart({
  series,
  entryIndex,
  exitIndex,
  revealed,
  gain,
  height = 360,
}: {
  series: ReplayPoint[];
  entryIndex: number;
  exitIndex: number;
  revealed: number;
  gain: boolean;
  height?: number;
}) {
  const closes = series.map((p) => p.close);
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const pad = (max - min) * 0.12 || 1;
  const accent = gain ? "#2dd4bf" : "#f87171";

  const head = Math.min(revealed, series.length - 1);
  const entryDate = series[entryIndex]?.date;
  const exitDate = series[exitIndex]?.date;
  const showExit = revealed >= exitIndex;

  const data = series.map((p, i) => ({
    date: p.date,
    context: i <= entryIndex ? p.close : null,
    active: i >= entryIndex && i <= revealed ? p.close : null,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 12, right: 18, left: -8, bottom: 0 }}>
        <defs>
          <linearGradient id="replayFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.38} />
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
          width={54}
          domain={[min - pad, max + pad]}
          tickFormatter={(v: number) => `$${v.toFixed(0)}`}
        />
        <ReferenceLine
          x={entryDate}
          stroke="#2dd4bf"
          strokeDasharray="4 3"
          strokeOpacity={0.75}
          label={{ value: "BUY", position: "insideTopLeft", fill: "#2dd4bf", fontSize: 11, fontWeight: 700 }}
        />
        {showExit && (
          <ReferenceLine
            x={exitDate}
            stroke={accent}
            strokeDasharray="4 3"
            strokeOpacity={0.75}
            label={{ value: "EXIT", position: "insideTopRight", fill: accent, fontSize: 11, fontWeight: 700 }}
          />
        )}
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
            y={series[head].close}
            r={4.5}
            fill={accent}
            stroke="#04060c"
            strokeWidth={2}
            isFront
          />
        )}
      </AreaChart>
    </ResponsiveContainer>
  );
}
