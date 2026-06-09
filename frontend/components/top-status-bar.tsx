"use client";

import {
  Menu,
  Radio,
  Clock,
  Boxes,
  Database,
  FlaskConical,
  type LucideIcon,
} from "lucide-react";
import { marketContext, tickerTape } from "@/lib/mock-data";
import { cn, formatSignedPct } from "@/lib/utils";

function StatusChip({
  icon: Icon,
  label,
  value,
  tone = "default",
}: {
  icon: LucideIcon;
  label: string;
  value: string;
  tone?: "default" | "bull" | "brand";
}) {
  return (
    <div className="flex items-center gap-2 whitespace-nowrap">
      <Icon
        className={cn(
          "size-3.5",
          tone === "bull" && "text-bull",
          tone === "brand" && "text-brand-300",
          tone === "default" && "text-slate-500"
        )}
      />
      <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </span>
      <span
        className={cn(
          "font-mono text-xs font-medium",
          tone === "bull" ? "text-bull-soft" : "text-slate-200"
        )}
      >
        {value}
      </span>
    </div>
  );
}

export function TopStatusBar({ onMenu }: { onMenu?: () => void }) {
  return (
    <header className="sticky top-0 z-30 border-b border-white/6 bg-ink-950/70 backdrop-blur-xl">
      {/* Main status row */}
      <div className="flex h-16 items-center gap-4 px-4 sm:px-6">
        <button
          onClick={onMenu}
          className="grid size-9 place-items-center rounded-lg border border-white/8 text-slate-300 hover:bg-white/[0.05] lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </button>

        <div className="flex items-center gap-2">
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-bull/60" />
            <span className="relative inline-flex size-2 rounded-full bg-bull" />
          </span>
          <span className="text-sm font-medium text-white">
            Market{" "}
            <span className="text-bull-soft">{marketContext.market}</span>
          </span>
        </div>

        <div className="ml-auto hidden items-center gap-5 md:flex">
          <StatusChip icon={Database} label="Universe" value={marketContext.universe} />
          <div className="h-4 w-px bg-white/8" />
          <StatusChip icon={Boxes} label="Model" value={marketContext.model} tone="brand" />
          <div className="h-4 w-px bg-white/8" />
          <StatusChip icon={Clock} label="Updated" value={marketContext.lastUpdated} />
          <div className="h-4 w-px bg-white/8" />
          <StatusChip icon={FlaskConical} label="Mode" value="Paper" tone="bull" />
        </div>

        <div className="ml-auto md:ml-0">
          <span className="hidden items-center gap-1.5 rounded-lg border border-brand-400/25 bg-brand-500/8 px-2.5 py-1.5 font-mono text-[10px] text-brand-200 sm:inline-flex">
            <Radio className="size-3 animate-pulse" /> LIVE
          </span>
        </div>
      </div>

      {/* Ticker tape */}
      <div className="relative overflow-hidden border-t border-white/6 bg-ink-950/40">
        <div className="mask-fade-x flex">
          <div className="flex shrink-0 animate-marquee items-center gap-6 py-1.5 pr-6">
            {[...tickerTape, ...tickerTape].map((t, i) => (
              <div key={i} className="flex items-center gap-1.5 whitespace-nowrap">
                <span className="font-mono text-[11px] font-medium text-slate-300">
                  {t.sym}
                </span>
                <span className="font-mono text-[11px] text-slate-500 data">
                  {t.price.toLocaleString()}
                </span>
                <span
                  className={cn(
                    "font-mono text-[11px] data",
                    t.chg >= 0 ? "text-bull-soft" : "text-bear-soft"
                  )}
                >
                  {formatSignedPct(t.chg)}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </header>
  );
}
