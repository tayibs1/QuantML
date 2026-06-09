"use client";

import { useMemo } from "react";
import { motion } from "motion/react";
import { cn } from "@/lib/utils";
import { seeded } from "@/lib/utils";

interface AnimatedGridBackgroundProps {
  className?: string;
  /** Density of floating particles. */
  particles?: number;
  /** Show large drifting glow orbs. */
  orbs?: boolean;
  /** Show the animated scan line. */
  scan?: boolean;
  /** Show the static CSS grid (disable when a shader already draws one). */
  grid?: boolean;
}

export function AnimatedGridBackground({
  className,
  particles = 22,
  orbs = true,
  scan = false,
  grid = true,
}: AnimatedGridBackgroundProps) {
  const dots = useMemo(() => {
    const rand = seeded(99);
    return Array.from({ length: particles }, (_, i) => ({
      id: i,
      x: rand() * 100,
      y: rand() * 100,
      size: 1 + rand() * 2,
      delay: rand() * 6,
      duration: 6 + rand() * 8,
      drift: 12 + rand() * 24,
    }));
  }, [particles]);

  return (
    <div
      className={cn(
        "pointer-events-none absolute inset-0 overflow-hidden",
        className
      )}
      aria-hidden
    >
      {/* Static grid */}
      {grid && <div className="absolute inset-0 grid-overlay" />}

      {/* Drifting glow orbs */}
      {orbs && (
        <>
          <motion.div
            className="absolute -left-32 top-0 size-[600px] rounded-full bg-brand-500/20 blur-[140px]"
            animate={{ x: [0, 80, 0], y: [0, 60, 0] }}
            transition={{ duration: 18, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute -right-24 top-1/3 size-[540px] rounded-full bg-violet/20 blur-[140px]"
            animate={{ x: [0, -60, 0], y: [0, 70, 0] }}
            transition={{ duration: 22, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute left-1/3 bottom-1/4 size-[360px] rounded-full bg-brand-400/10 blur-[100px]"
            animate={{ x: [0, 40, -20, 0], y: [0, -30, 20, 0] }}
            transition={{ duration: 28, repeat: Infinity, ease: "easeInOut" }}
          />
        </>
      )}

      {/* Floating particles */}
      {dots.map((d) => (
        <motion.span
          key={d.id}
          className="absolute rounded-full bg-brand-300/60"
          style={{
            left: `${d.x}%`,
            top: `${d.y}%`,
            width: d.size,
            height: d.size,
            boxShadow: "0 0 8px rgba(45,212,191,0.6)",
          }}
          animate={{ y: [0, -d.drift, 0], opacity: [0.25, 0.85, 0.25] }}
          transition={{
            duration: d.duration,
            repeat: Infinity,
            ease: "easeInOut",
            delay: d.delay,
          }}
        />
      ))}

      {/* Scan line */}
      {scan && (
        <motion.div
          className="absolute inset-x-0 h-px bg-gradient-to-r from-transparent via-brand-400/40 to-transparent"
          animate={{ top: ["0%", "100%"] }}
          transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
        />
      )}
    </div>
  );
}
