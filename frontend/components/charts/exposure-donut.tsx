"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { ChartTooltip } from "./chart-tooltip";

const PALETTE = [
  "#2dd4bf",
  "#22c55e",
  "#8b5cf6",
  "#38bdf8",
  "#f59e0b",
  "#fb7185",
  "rgba(148,163,184,0.4)",
];

export function ExposureDonut({
  data,
  height = 220,
}: {
  data: { name: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Tooltip content={<ChartTooltip valueFormatter={(v) => `${v}%`} />} />
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="58%"
          outerRadius="86%"
          paddingAngle={2}
          stroke="rgba(4,6,12,0.6)"
          strokeWidth={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
      </PieChart>
    </ResponsiveContainer>
  );
}

export { PALETTE as exposurePalette };
