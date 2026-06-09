"use client";

import { motion, useInView } from "motion/react";
import { useRef } from "react";

export function ConfidenceRing({
  value,
  color = "#2dd4bf",
  size = 56,
  stroke = 5,
}: {
  value: number;
  color?: string;
  size?: number;
  stroke?: number;
}) {
  const ref = useRef<SVGSVGElement>(null);
  const inView = useInView(ref, { once: true });
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (value / 100) * c;

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <svg ref={ref} width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={stroke}
        />
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          initial={{ strokeDashoffset: c }}
          animate={inView ? { strokeDashoffset: offset } : { strokeDashoffset: c }}
          transition={{ duration: 1.1, ease: [0.21, 0.6, 0.35, 1] }}
          style={{ filter: `drop-shadow(0 0 4px ${color}80)` }}
        />
      </svg>
      <div className="absolute inset-0 grid place-items-center">
        <span className="font-mono text-sm font-semibold text-white data">
          {value}
        </span>
      </div>
    </div>
  );
}
