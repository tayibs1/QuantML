import Link from "next/link";
import { cn } from "@/lib/utils";

export function Logo({
  className,
  href = "/",
  compact = false,
}: {
  className?: string;
  href?: string;
  compact?: boolean;
}) {
  return (
    <Link
      href={href}
      className={cn("group inline-flex items-center gap-2.5", className)}
    >
      <span className="relative grid size-9 place-items-center rounded-xl border border-brand-400/30 bg-brand-500/10 shadow-glow">
        <span className="absolute inset-0 rounded-xl bg-brand-500/10 blur-md transition-opacity group-hover:opacity-100" />
        <svg
          viewBox="0 0 24 24"
          className="relative size-5 text-brand-300"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M3 17l5-5 3 3 4-6 4 5" />
          <circle cx="8" cy="12" r="1.4" fill="currentColor" stroke="none" />
          <circle cx="11" cy="15" r="1.4" fill="currentColor" stroke="none" />
          <circle cx="15" cy="9" r="1.4" fill="currentColor" stroke="none" />
        </svg>
      </span>
      {!compact && (
        <span className="flex flex-col leading-none">
          <span className="text-[15px] font-semibold tracking-tight text-white">
            Quant<span className="text-brand-300">ML</span>
          </span>
          <span className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-500">
            Research Terminal
          </span>
        </span>
      )}
    </Link>
  );
}
