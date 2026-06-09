"use client";

import { useEffect, useState } from "react";
import { Filter, RefreshCw, Loader2 } from "lucide-react";
import { PageTransition } from "@/components/motion-primitives";
import { PageHeader } from "@/components/page-header";
import { SignalCard } from "@/components/signal-card";
import { GlassPanel } from "@/components/glass-panel";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api } from "@/lib/api";
import { signals as mockSignals, type Signal } from "@/lib/mock-data";

const FILTERS = ["All", "BUY", "HOLD", "AVOID"] as const;

export default function SignalsPage() {
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("All");
  const [data, setData] = useState<Signal[]>(mockSignals);
  const [live, setLive] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api
      .signals()
      .then((d) => {
        if (Array.isArray(d) && d.length) {
          setData(d as Signal[]);
          setLive(true);
        }
      })
      .catch(() => setLive(false))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    api
      .signals()
      .then((d) => {
        if (active && Array.isArray(d) && d.length) {
          setData(d as Signal[]);
          setLive(true);
        }
      })
      .catch(() => active && setLive(false))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, []);

  const filtered = filter === "All" ? data : data.filter((s) => s.signal === filter);
  const counts = {
    BUY: data.filter((s) => s.signal === "BUY").length,
    HOLD: data.filter((s) => s.signal === "HOLD").length,
    AVOID: data.filter((s) => s.signal === "AVOID").length,
  };

  return (
    <PageTransition className="space-y-6">
      <PageHeader
        eyebrow="Model Predictions"
        title="Trading Signals"
        description="Probabilistic buy / hold / avoid signals with confidence, expected return and the feature drivers behind each call."
        actions={
          <>
            <Badge variant={live ? "bull" : "outline"} className="hidden sm:inline-flex">
              <span className={`size-1.5 rounded-full ${live ? "bg-bull" : "bg-slate-500"}`} />
              {live ? "Live model" : "Sample data"}
            </Badge>
            <Button variant="secondary" size="sm">
              <Filter className="size-4" /> Filters
            </Button>
            <Button size="sm" onClick={load} disabled={loading}>
              {loading ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}
              Refresh
            </Button>
          </>
        }
      />

      {/* Summary strip */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Active Signals", value: data.length, tone: "text-white" },
          { label: "Buy", value: counts.BUY, tone: "text-bull-soft" },
          { label: "Hold", value: counts.HOLD, tone: "text-hold-soft" },
          { label: "Avoid", value: counts.AVOID, tone: "text-bear-soft" },
        ].map((s) => (
          <GlassPanel key={s.label} inset className="py-3.5">
            <div className="text-[10px] uppercase tracking-wider text-slate-500">
              {s.label}
            </div>
            <div className={`mt-1 font-mono text-2xl font-semibold data ${s.tone}`}>
              {s.value}
            </div>
          </GlassPanel>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <Tabs value={filter} onValueChange={(v) => setFilter(v as typeof filter)}>
          <TabsList>
            {FILTERS.map((f) => (
              <TabsTrigger key={f} value={f}>
                {f === "All" ? "All Signals" : f}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <span className="hidden font-mono text-xs text-slate-500 sm:block">
          {filtered.length} result{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {filtered.map((s, i) => (
          <SignalCard key={s.ticker} signal={s} index={i} />
        ))}
      </div>
    </PageTransition>
  );
}
