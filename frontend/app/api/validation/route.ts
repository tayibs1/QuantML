import { NextResponse } from "next/server";

// GET /api/validation - robustness studies (rolling-window + training-window sweep).
// Same shape the FastAPI backend serves from data/research/*.json. Numbers here are
// representative sample data; the live backend serves the real measured results.

function weeklySeries() {
  // a deterministic, gently-trending sample series for the sparkline
  const out: { date: string; basketReturn: number; accuracy: number; nBuy: number }[] = [];
  let d = new Date("2024-01-05");
  for (let i = 0; i < 26; i++) {
    const wobble = Math.sin(i / 3) * 0.004 + (i % 5 === 0 ? -0.006 : 0.002);
    out.push({
      date: d.toISOString().slice(0, 10),
      basketReturn: Number((0.003 + wobble).toFixed(4)),
      accuracy: Number((0.37 + Math.sin(i / 4) * 0.03).toFixed(3)),
      nBuy: 12 + (i % 4),
    });
    d = new Date(d.getTime() + 7 * 86_400_000);
  }
  return out;
}

export function GET() {
  return NextResponse.json({
    rollingWindow: {
      note: "Anchored weekly walk-forward (refit each week on prior data only).",
      generatedAt: "2026-06-16",
      baseline: { sharpe: 1.19, cagr: 0.3117, maxDrawdown: -0.293, auc: 0.54, accuracy: 0.366, buy_hit_rate: 0.5282 },
      rolling: { sharpe: 1.15, cagr: 0.298, maxDrawdown: -0.3496, auc: 0.5327, accuracy: 0.3648, hitRate: 0.5882, volatility: 0.257, weeks: 323 },
      weekly: weeklySeries(),
    },
    windowComparison: {
      note: "Anchored weekly scheme at each look-back, aligned to the same evaluation weeks.",
      generatedAt: "2026-06-16",
      step: 10,
      windows: {
        "2y": { sharpe: 1.46, cagr: 0.3964, maxDrawdown: -0.2203, volatility: 0.2509, hitRate: 0.6066, weeks: 61 },
        "3y": { sharpe: 1.75, cagr: 0.4726, maxDrawdown: -0.2396, volatility: 0.2376, hitRate: 0.6721, weeks: 61 },
        "4y": { sharpe: 1.9, cagr: 0.5373, maxDrawdown: -0.2209, volatility: 0.2426, hitRate: 0.623, weeks: 61 },
        "5y": { sharpe: 1.66, cagr: 0.4647, maxDrawdown: -0.2111, volatility: 0.2499, hitRate: 0.6393, weeks: 61 },
        expanding: { sharpe: 1.77, cagr: 0.4905, maxDrawdown: -0.1952, volatility: 0.2433, hitRate: 0.6721, weeks: 61 },
      },
      bestBySharpe: "4y",
      steadiestByVol: "3y",
    },
    regimeModels: {
      general: { sharpe: 1.19, auc: 0.54 },
      ensemble: { sharpe: 0.95, auc: 0.537 },
      year2022: { general: -0.77, ensemble: -0.5 },
      ensembleBeatsGeneral: false,
      verdict:
        "Regime ensemble Sharpe 0.95 vs general 1.19 — no overall improvement; general model stays champion. It did soften the 2022 bear drawdown (-0.50 vs -0.77), but the thin bear sample makes the specialist too noisy to ship.",
    },
    ood: {
      trainEnd: "2023-01-01",
      trainRows: 55342,
      testRows: 47872,
      metrics: { sharpe: 1.89, auc: 0.54, accuracy: 0.366 },
      overallDrift: "OK",
      eraDrift: [
        { feature: "dist_52w_low", label: "Distance from 52w low", psi: 0.023, status: "OK" },
        { feature: "vol_of_vol", label: "Volatility of volatility", psi: 0.015, status: "OK" },
        { feature: "vol_60", label: "60-day volatility", psi: 0.013, status: "OK" },
      ],
    },
    confidence: {
      sizing: {
        equalWeight: { sharpe: 1.19, maxDrawdown: -0.293 },
        confidenceWeighted: { sharpe: 1.21, maxDrawdown: -0.2969 },
      },
      confidenceImprovesSharpe: true,
      calibration: { brier: 0.227, ece: 0.0432, bins: [] },
    },
    onlineLearning: {
      cadences: {
        weekly: { refitEvery: 1, refits: 76, seconds: 745.9, sharpe: 1.5, hitRate: 0.61, weeks: 76 },
        biweekly: { refitEvery: 2, refits: 38, seconds: 323.4, sharpe: 1.67, hitRate: 0.63, weeks: 76 },
        monthly: { refitEvery: 4, refits: 19, seconds: 152.7, sharpe: 1.63, hitRate: 0.62, weeks: 76 },
        quarterly: { refitEvery: 12, refits: 7, seconds: 59.2, sharpe: 1.44, hitRate: 0.59, weeks: 76 },
      },
      fullRetrainSharpe: 1.5,
    },
  });
}
