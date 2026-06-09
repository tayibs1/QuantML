"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "motion/react";
import { Activity, ChevronRight } from "lucide-react";
import { Logo } from "./logo";
import { navItems } from "@/lib/nav";
import { cn } from "@/lib/utils";

export function DashboardSidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center border-b border-white/6 px-5">
        <Logo />
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-5 no-scrollbar">
        <p className="px-3 pb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-600">
          Workspace
        </p>
        {navItems.map((item) => {
          const active =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors",
                active
                  ? "text-white"
                  : "text-slate-400 hover:text-slate-100"
              )}
            >
              {active && (
                <motion.span
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-xl border border-brand-400/25 bg-brand-500/10 shadow-[inset_0_0_0_1px_rgba(45,212,191,0.15)]"
                  transition={{ type: "spring", stiffness: 380, damping: 32 }}
                />
              )}
              <Icon
                className={cn(
                  "relative size-[18px] transition-colors",
                  active ? "text-brand-300" : "text-slate-500 group-hover:text-slate-300"
                )}
              />
              <span className="relative flex-1 font-medium">{item.label}</span>
              {item.badge && (
                <span className="relative rounded-md bg-white/[0.06] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
                  {item.badge}
                </span>
              )}
              {active && (
                <ChevronRight className="relative size-3.5 text-brand-300/70" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* Model status footer */}
      <div className="border-t border-white/6 p-3">
        <div className="rounded-xl border border-white/8 bg-white/[0.02] p-3">
          <div className="flex items-center gap-2">
            <span className="relative flex size-2">
              <span className="absolute inline-flex size-full animate-ping rounded-full bg-bull/60" />
              <span className="relative inline-flex size-2 rounded-full bg-bull" />
            </span>
            <span className="text-xs font-medium text-slate-200">
              XGBoost-v3 live
            </span>
          </div>
          <div className="mt-2 flex items-center justify-between font-mono text-[10px] text-slate-500">
            <span className="flex items-center gap-1">
              <Activity className="size-3" /> drift: low
            </span>
            <span>paper mode</span>
          </div>
        </div>
      </div>
    </div>
  );
}
