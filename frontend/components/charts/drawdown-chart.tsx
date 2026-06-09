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

export function DrawdownChart({
  data = equitySeries,
  height = 200,
}: {
  data?: MetricPoint[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <defs>
          <linearGradient id="ddFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f43f5e" stopOpacity={0} />
            <stop offset="100%" stopColor="#f43f5e" stopOpacity={0.4} />
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
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
        />
        <Tooltip
          content={<ChartTooltip valueFormatter={(v) => `${v.toFixed(2)}%`} />}
        />
        <Area
          type="monotone"
          dataKey="drawdown"
          name="Drawdown"
          stroke="#fb7185"
          strokeWidth={1.5}
          fill="url(#ddFill)"
          dot={false}
          activeDot={{ r: 3, fill: "#fb7185" }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
