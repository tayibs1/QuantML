"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { volatilityRegime } from "@/lib/mock-data";
import { ChartTooltip } from "./chart-tooltip";

const axisStyle = {
  fontSize: 10,
  fontFamily: "var(--font-mono)",
  fill: "rgba(148,163,184,0.6)",
};

export function VolatilityChart({
  height = 240,
  data = volatilityRegime,
}: {
  height?: number;
  data?: { t: number; vix: number; realized: number }[];
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart
        data={data}
        margin={{ top: 8, right: 8, left: -16, bottom: 0 }}
      >
        <defs>
          <linearGradient id="volFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.3} />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(255,255,255,0.05)"
          vertical={false}
        />
        <XAxis dataKey="t" tick={axisStyle} tickLine={false} axisLine={false} />
        <YAxis
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          width={40}
          tickFormatter={(v: number) => `${v.toFixed(0)}`}
        />
        <Tooltip content={<ChartTooltip valueFormatter={(v) => v.toFixed(1)} />} />
        <Area
          type="monotone"
          dataKey="vix"
          name="Implied (VIX)"
          stroke="#f59e0b"
          strokeWidth={2}
          fill="url(#volFill)"
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="realized"
          name="Realized"
          stroke="#2dd4bf"
          strokeWidth={1.5}
          dot={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
