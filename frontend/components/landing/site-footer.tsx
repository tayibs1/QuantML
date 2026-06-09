import Link from "next/link";
import { Logo } from "@/components/logo";
import { navItems } from "@/lib/nav";

export function SiteFooter() {
  return (
    <footer className="relative border-t border-white/6 bg-ink-950/60">
      <div className="mx-auto max-w-6xl px-6 py-12">
        <div className="flex flex-col gap-8 md:flex-row md:justify-between">
          <div className="max-w-sm">
            <Logo />
            <p className="mt-4 text-sm leading-relaxed text-slate-500">
              A production ML research platform for trading signals, risk-aware
              backtesting, and RAG-based market analysis.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-8 sm:grid-cols-3">
            <div>
              <p className="label-eyebrow mb-3">Platform</p>
              <ul className="space-y-2">
                {navItems.slice(0, 4).map((n) => (
                  <li key={n.href}>
                    <Link
                      href={n.href}
                      className="text-sm text-slate-400 transition-colors hover:text-white"
                    >
                      {n.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="label-eyebrow mb-3">Research</p>
              <ul className="space-y-2">
                {navItems.slice(4).map((n) => (
                  <li key={n.href}>
                    <Link
                      href={n.href}
                      className="text-sm text-slate-400 transition-colors hover:text-white"
                    >
                      {n.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="label-eyebrow mb-3">System</p>
              <ul className="space-y-2 font-mono text-xs text-slate-500">
                <li className="flex items-center gap-1.5">
                  <span className="size-1.5 rounded-full bg-bull" /> API: operational
                </li>
                <li>Model: XGBoost-v3</li>
                <li>Mode: paper</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-10 rounded-xl border border-white/6 bg-white/[0.02] p-4">
          <p className="text-xs leading-relaxed text-slate-500">
            <span className="font-mono uppercase tracking-wider text-slate-400">
              Disclaimer ·{" "}
            </span>
            QuantML is a research and educational platform. It does not provide
            financial advice, execute trades, or guarantee profitable outcomes.
            All signals are experimental and should be evaluated through rigorous
            backtesting and paper trading before any real-world use. Past
            performance is not indicative of future results.
          </p>
        </div>

        <div className="mt-6 flex flex-col items-center justify-between gap-3 text-xs text-slate-600 sm:flex-row">
          <span>© {new Date().getFullYear()} QuantML. Research before you trade.</span>
          <span className="font-mono">Built for research · not for execution</span>
        </div>
      </div>
    </footer>
  );
}
