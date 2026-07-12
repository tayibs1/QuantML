"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, Maximize2, Minimize2, Clapperboard } from "lucide-react";
import { DashboardSidebar } from "./dashboard-sidebar";
import { TopStatusBar } from "./top-status-bar";
import { CinematicProvider } from "@/lib/cinematic";
import { cn } from "@/lib/utils";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [cinematic, setCinematic] = useState(false);

  const enterCinematic = useCallback(async () => {
    setMobileOpen(false);
    setCinematic(true);
    try {
      await document.documentElement.requestFullscreen?.();
    } catch {
      // fullscreen can be blocked; the layout still applies
    }
  }, []);

  const exitCinematic = useCallback(async () => {
    setCinematic(false);
    try {
      if (document.fullscreenElement) await document.exitFullscreen?.();
    } catch {
      /* noop */
    }
  }, []);

  // catch the user leaving fullscreen from the browser itself
  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement) setCinematic(false);
    };
    document.addEventListener("fullscreenchange", onFsChange);
    return () => document.removeEventListener("fullscreenchange", onFsChange);
  }, []);

  // Esc exits even if fullscreen was never granted
  useEffect(() => {
    if (!cinematic) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") exitCinematic();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cinematic, exitCinematic]);

  return (
    <div className="relative min-h-screen">
      {/* sidebar, hidden in cinematic */}
      {!cinematic && (
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-white/6 bg-ink-900/60 backdrop-blur-xl lg:block">
          <DashboardSidebar />
        </aside>
      )}

      {/* Mobile drawer */}
      <AnimatePresence>
        {mobileOpen && !cinematic && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            />
            <motion.aside
              initial={{ x: "-100%" }}
              animate={{ x: 0 }}
              exit={{ x: "-100%" }}
              transition={{ type: "spring", stiffness: 360, damping: 38 }}
              className="fixed inset-y-0 left-0 z-50 w-72 border-r border-white/8 bg-ink-900/95 backdrop-blur-xl lg:hidden"
            >
              <button
                onClick={() => setMobileOpen(false)}
                className="absolute right-3 top-4 grid size-8 place-items-center rounded-lg text-slate-400 hover:bg-white/[0.06]"
                aria-label="Close navigation"
              >
                <X className="size-4" />
              </button>
              <DashboardSidebar onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </>
        )}
      </AnimatePresence>

      {/* Main column */}
      <div className={cn(!cinematic && "lg:pl-64")}>
        {!cinematic && <TopStatusBar onMenu={() => setMobileOpen(true)} />}
        <main
          className={cn(
            cinematic ? "h-screen overflow-hidden p-4 sm:p-6" : "px-4 py-6 sm:px-6 lg:px-8"
          )}
        >
          <CinematicProvider value={cinematic}>
            <FitToScreen active={cinematic}>{children}</FitToScreen>
          </CinematicProvider>
        </main>
      </div>

      {/* Cinematic controls */}
      {!cinematic ? (
        <button
          onClick={enterCinematic}
          className="fixed bottom-5 right-5 z-50 flex items-center gap-2 rounded-full border border-white/10 bg-ink-900/80 px-3.5 py-2 font-mono text-[11px] uppercase tracking-wider text-slate-300 shadow-panel backdrop-blur-xl transition-colors hover:border-brand-400/40 hover:text-white"
          aria-label="Enter cinematic mode"
        >
          <Clapperboard className="size-4 text-brand-300" />
          Cinematic
        </button>
      ) : (
        <button
          onClick={exitCinematic}
          className="group fixed right-4 top-4 z-[60] flex items-center gap-2 rounded-full border border-white/10 bg-ink-900/70 px-3 py-1.5 font-mono text-[10px] uppercase tracking-wider text-slate-400 opacity-40 backdrop-blur-xl transition-opacity hover:opacity-100"
          aria-label="Exit cinematic mode"
        >
          <Minimize2 className="size-3.5" />
          Exit
          <span className="hidden text-slate-600 group-hover:inline">· Esc</span>
        </button>
      )}
    </div>
  );
}

// Scales children down so the page fits the viewport without scrolling.
function FitToScreen({ active, children }: { active: boolean; children: React.ReactNode }) {
  const outerRef = useRef<HTMLDivElement | null>(null);
  const innerRef = useRef<HTMLDivElement | null>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    if (!active) {
      setScale(1);
      return;
    }
    const compute = () => {
      const o = outerRef.current;
      const i = innerRef.current;
      if (!o || !i) return;
      const availH = o.clientHeight;
      const availW = o.clientWidth;
      const contentH = i.scrollHeight;
      const contentW = i.scrollWidth;
      if (!contentH || !contentW) return;
      const next = Math.min(1, availH / contentH, availW / contentW);
      // floor so very long pages don't shrink to nothing
      setScale(Math.max(0.3, Math.round(next * 1000) / 1000));
    };
    compute();
    const ro = new ResizeObserver(compute);
    if (outerRef.current) ro.observe(outerRef.current);
    if (innerRef.current) ro.observe(innerRef.current);
    window.addEventListener("resize", compute);
    // recheck once the fullscreen transition finishes
    const t = window.setTimeout(compute, 350);
    return () => {
      ro.disconnect();
      window.removeEventListener("resize", compute);
      window.clearTimeout(t);
    };
  }, [active, children]);

  if (!active) return <>{children}</>;

  return (
    <div ref={outerRef} className="flex h-full w-full items-start justify-center overflow-hidden">
      <div
        ref={innerRef}
        style={{ transform: `scale(${scale})`, transformOrigin: "top center" }}
        className="w-full max-w-[1600px]"
      >
        {children}
      </div>
    </div>
  );
}
