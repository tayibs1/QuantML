import type { MetricPoint } from "@/lib/mock-data";

// Re-prices the backtest snapshot for whatever the cost sliders are set to.
// The snapshot is net of 13 bps at a weekly cadence, so we strip that baseline
// out of each step and re-apply the user's cost instead.

export type CostCard = { label: string; value: string; tone: "bull" | "bear" | "neutral" };
export type Rebalance = "Daily" | "Weekly" | "Monthly";
export type CostCfg = { commissionBps: number; slippageBps: number; rebalance: Rebalance };

const BASE_BPS = 13; // 5 commission + 8 slippage
const BASE_FREQ = 1; // weekly
const FREQ: Record<Rebalance, number> = { Daily: 2.2, Weekly: 1, Monthly: 0.45 };
const FALLBACK_TURNOVER = 46.82; // used if the turnover card is missing

const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));
const num = (v: string) => parseFloat(v.replace(/[^0-9.\-]/g, "")) || 0;
const r2 = (v: number) => Math.round(v * 100) / 100;

function totalTurnoverFrac(cards: CostCard[]): number {
  const t = cards.find((c) => c.label.toLowerCase().startsWith("turnover"));
  return t ? num(t.value) / 100 : FALLBACK_TURNOVER;
}

interface CurveMetrics {
  cagr: number;
  vol: number;
  sharpe: number;
  sortino: number;
  mdd: number;
}

function curveMetrics(eq: MetricPoint[]): CurveMetrics {
  const years =
    (new Date(eq[eq.length - 1].date).getTime() - new Date(eq[0].date).getTime()) /
      (365.25 * 24 * 3600 * 1000) || 1;
  const cagr = Math.pow(eq[eq.length - 1].strategy / eq[0].strategy, 1 / years) - 1;

  const rets: number[] = [];
  for (let i = 1; i < eq.length; i++) rets.push(eq[i].strategy / eq[i - 1].strategy - 1);
  const ppy = rets.length / years;
  const mean = rets.reduce((a, b) => a + b, 0) / (rets.length || 1);
  const variance = rets.reduce((a, b) => a + (b - mean) ** 2, 0) / (rets.length || 1);
  const sd = Math.sqrt(variance);
  const neg = rets.filter((r) => r < 0);
  const dnsd = Math.sqrt(neg.reduce((a, b) => a + b * b, 0) / (neg.length || 1));

  const vol = sd * Math.sqrt(ppy);
  const sharpe = sd > 0 ? (mean * Math.sqrt(ppy)) / sd : 0;
  const sortino = dnsd > 0 ? (mean * Math.sqrt(ppy)) / dnsd : 0;

  let peak = eq[0].strategy;
  let mdd = 0;
  for (const p of eq) {
    peak = Math.max(peak, p.strategy);
    mdd = Math.min(mdd, p.strategy / peak - 1);
  }
  return { cagr, vol, sharpe, sortino, mdd };
}

function reCard(c: CostCard, now: CurveMetrics, base: CurveMetrics, freq: number, turnover: number): CostCard {
  const label = c.label.toLowerCase();
  const b = num(c.value);
  if (label.startsWith("cagr")) {
    const v = b + (now.cagr - base.cagr) * 100;
    return { label: c.label, value: `${v.toFixed(1)}%`, tone: v >= 0 ? "bull" : "bear" };
  }
  if (label.startsWith("sharpe")) return { ...c, value: (b + (now.sharpe - base.sharpe)).toFixed(2) };
  if (label.startsWith("sortino")) return { ...c, value: (b + (now.sortino - base.sortino)).toFixed(2) };
  if (label.startsWith("max")) {
    const v = b + (now.mdd - base.mdd) * 100;
    return { label: c.label, value: `${v.toFixed(1)}%`, tone: "bear" };
  }
  if (label.startsWith("vol")) return { ...c, value: `${(b + (now.vol - base.vol) * 100).toFixed(1)}%` };
  if (label.startsWith("turnover")) return { ...c, value: `${Math.round(turnover * 100 * freq)}%` };
  return c; // win rate / profit factor don't move with cost
}

export function applyCostModel(
  equity: MetricPoint[],
  cards: CostCard[],
  cfg: CostCfg,
): { equity: MetricPoint[]; summaryCards: CostCard[] } {
  if (!equity || equity.length < 2) return { equity, summaryCards: cards };

  const nSteps = equity.length - 1;
  const total = totalTurnoverFrac(cards);
  const perStep = total / nSteps;
  const cNew = clamp(cfg.commissionBps, 0, 30) + clamp(cfg.slippageBps, 0, 50);
  const freq = FREQ[cfg.rebalance] ?? 1;

  const k0 = (BASE_BPS / 10000) * perStep * BASE_FREQ; // strip baseline cost
  const kNew = (cNew / 10000) * perStep * freq; // apply new cost

  const out: MetricPoint[] = [{ ...equity[0], strategy: 100, drawdown: 0 }];
  let peak = 100;
  for (let i = 1; i < equity.length; i++) {
    const gross = equity[i].strategy / equity[i - 1].strategy - 1 + k0;
    const strat = out[i - 1].strategy * (1 + gross - kNew);
    peak = Math.max(peak, strat);
    out.push({
      date: equity[i].date,
      strategy: r2(strat),
      benchmark: equity[i].benchmark,
      drawdown: r2((strat / peak - 1) * 100),
    });
  }

  const now = curveMetrics(out);
  const base = curveMetrics(equity);
  const summaryCards = cards.map((c) => reCard(c, now, base, freq, total));
  return { equity: out, summaryCards };
}
