"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { equitySeries, type MetricPoint } from "@/lib/mock-data";
import { ChartTooltip } from "./chart-tooltip";

const axisStyle = {
  fontSize: 10,
  fontFamily: "var(--font-mono)",
  fill: "rgba(148,163,184,0.6)",
};

export function EquityCurveChart({
  data = equitySeries,
  showBenchmark = true,
  height = 300,
}: {
  data?: MetricPoint[];
  showBenchmark?: boolean;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="eqStrategy" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#2dd4bf" stopOpacity={0.45} />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="eqBench" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#8b5cf6" stopOpacity={0.2} />
            <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke="rgba(255,255,255,0.05)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          minTickGap={48}
          tickFormatter={(v: string) => v.slice(2, 7)}
        />
        <YAxis
          tick={axisStyle}
          tickLine={false}
          axisLine={false}
          width={48}
          domain={["dataMin - 4", "dataMax + 4"]}
          tickFormatter={(v: number) => `${v.toFixed(0)}`}
        />
        <Tooltip
          content={
            <ChartTooltip valueFormatter={(v) => `${v.toFixed(2)}`} />
          }
        />
        {showBenchmark && (
          <Area
            type="monotone"
            dataKey="benchmark"
            name="QQQ"
            stroke="#a78bfa"
            strokeWidth={1.5}
            fill="url(#eqBench)"
            strokeDasharray="4 3"
            dot={false}
            activeDot={{ r: 3, fill: "#a78bfa" }}
          />
        )}
        <Area
          type="monotone"
          dataKey="strategy"
          name="Strategy"
          stroke="#2dd4bf"
          strokeWidth={2}
          fill="url(#eqStrategy)"
          dot={false}
          activeDot={{ r: 4, fill: "#2dd4bf", stroke: "#04060c", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
