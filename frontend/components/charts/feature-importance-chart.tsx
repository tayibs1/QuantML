"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { featureImportance } from "@/lib/mock-data";
import { ChartTooltip } from "./chart-tooltip";

export function FeatureImportanceChart({ height = 320 }: { height?: number }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart
        data={featureImportance}
        layout="vertical"
        margin={{ top: 0, right: 16, left: 8, bottom: 0 }}
      >
        <defs>
          <linearGradient id="fiBar" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.6} />
            <stop offset="100%" stopColor="#2dd4bf" stopOpacity={1} />
          </linearGradient>
        </defs>
        <XAxis type="number" hide domain={[0, "dataMax + 0.02"]} />
        <YAxis
          type="category"
          dataKey="feature"
          width={132}
          tick={{
            fontSize: 11,
            fontFamily: "var(--font-sans)",
            fill: "rgba(203,213,225,0.85)",
          }}
          tickLine={false}
          axisLine={false}
        />
        <Tooltip
          cursor={{ fill: "rgba(255,255,255,0.03)" }}
          content={
            <ChartTooltip valueFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
          }
        />
        <Bar dataKey="importance" name="Importance" radius={[0, 6, 6, 0]} barSize={14}>
          {featureImportance.map((_, i) => (
            <Cell key={i} fill="url(#fiBar)" />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
