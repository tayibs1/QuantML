"""
Deterministic mock data for the backend.

Mirrors lib/mock-data.ts. In a real deployment these would be backed by a
market-data store (OHLCV), a feature store, the model's predict_proba, a backtest
results table, and a vector store for RAG. The return shapes stay identical
either way, so the frontend never has to know which one it's talking to.
"""
from __future__ import annotations

import math
import random
from datetime import date, timedelta


def _rng(seed: int) -> random.Random:
    return random.Random(seed)


# --- time series ---
def equity_series(points: int = 180) -> list[dict]:
    r = _rng(42)
    strat = bench = peak = 100.0
    start = date(2024, 1, 1)
    out: list[dict] = []
    for i in range(points):
        strat *= 1 + (r.random() - 0.46) * 0.018 + 0.0011
        bench *= 1 + (r.random() - 0.48) * 0.016 + 0.0006
        peak = max(peak, strat)
        dd = (strat - peak) / peak * 100
        d = start + timedelta(days=i * 3)
        out.append(
            {
                "date": d.isoformat(),
                "strategy": round(strat, 2),
                "benchmark": round(bench, 2),
                "drawdown": round(dd, 2),
            }
        )
    return out


# --- dashboard metrics ---
METRICS = [
    {"key": "portfolio", "label": "Portfolio Value", "value": 1284500, "prefix": "$", "decimals": 0, "delta": 3.2, "spark": 1, "up": True},
    {"key": "strategy", "label": "Strategy Return", "value": 28.4, "suffix": "%", "decimals": 1, "delta": 28.4, "spark": 2, "up": True},
    {"key": "benchmark", "label": "Benchmark (QQQ)", "value": 17.6, "suffix": "%", "decimals": 1, "delta": 17.6, "spark": 3, "up": True},
    {"key": "sharpe", "label": "Sharpe Ratio", "value": 1.02, "decimals": 2, "delta": 0.08, "spark": 4, "up": True},
    {"key": "drawdown", "label": "Max Drawdown", "value": -15.4, "suffix": "%", "decimals": 1, "delta": -2.1, "spark": 5, "up": False},
    {"key": "winrate", "label": "Win Rate", "value": 57.3, "suffix": "%", "decimals": 1, "delta": 1.4, "spark": 6, "up": True},
    {"key": "confidence", "label": "Model Confidence", "value": 78, "suffix": "%", "decimals": 0, "delta": 4, "spark": 7, "up": True},
    {"key": "exposure", "label": "Current Exposure", "value": 64, "suffix": "%", "decimals": 0, "delta": -35, "spark": 8, "up": False},
]


# --- signals ---
SIGNALS = [
    {"ticker": "NVDA", "company": "NVIDIA Corp.", "signal": "BUY", "confidence": 78, "expectedReturn5d": 2.1, "risk": "High", "model": "XGBoost-v3", "drivers": ["Momentum (20d)", "Volume spike", "Relative strength", "Earnings revision"], "price": 121.4, "change": 1.8, "sector": "Semiconductors"},
    {"ticker": "MSFT", "company": "Microsoft Corp.", "signal": "HOLD", "confidence": 54, "expectedReturn5d": 0.4, "risk": "Low", "model": "XGBoost-v3", "drivers": ["Trend stability", "Low volatility", "Neutral flow"], "price": 441.2, "change": 0.3, "sector": "Software"},
    {"ticker": "AAPL", "company": "Apple Inc.", "signal": "BUY", "confidence": 66, "expectedReturn5d": 1.3, "risk": "Moderate", "model": "LightGBM-v2", "drivers": ["Mean reversion", "Options skew", "Seasonality"], "price": 228.9, "change": 0.9, "sector": "Hardware"},
    {"ticker": "AMZN", "company": "Amazon.com Inc.", "signal": "HOLD", "confidence": 51, "expectedReturn5d": -0.2, "risk": "Moderate", "model": "XGBoost-v3", "drivers": ["Range-bound", "Soft volume", "Macro overhang"], "price": 186.3, "change": -0.4, "sector": "E-commerce"},
    {"ticker": "TSLA", "company": "Tesla Inc.", "signal": "AVOID", "confidence": 71, "expectedReturn5d": -1.6, "risk": "Elevated", "model": "XGBoost-v3", "drivers": ["Negative momentum", "Elevated IV", "Deteriorating breadth"], "price": 246.7, "change": -2.7, "sector": "Automotive"},
    {"ticker": "GOOGL", "company": "Alphabet Inc.", "signal": "BUY", "confidence": 63, "expectedReturn5d": 1.1, "risk": "Moderate", "model": "LightGBM-v2", "drivers": ["Breakout", "Positive drift", "Sector rotation"], "price": 178.5, "change": 1.2, "sector": "Software"},
    {"ticker": "META", "company": "Meta Platforms", "signal": "BUY", "confidence": 69, "expectedReturn5d": 1.7, "risk": "Moderate", "model": "XGBoost-v3", "drivers": ["Momentum (60d)", "Earnings beat", "Flow imbalance"], "price": 504.1, "change": 1.5, "sector": "Software"},
    {"ticker": "AMD", "company": "Advanced Micro Devices", "signal": "AVOID", "confidence": 58, "expectedReturn5d": -0.9, "risk": "High", "model": "XGBoost-v3", "drivers": ["Weak relative strength", "Distribution days"], "price": 158.2, "change": -1.9, "sector": "Semiconductors"},
]


# --- models ---
MODELS = [
    {"id": "xgb-v3", "name": "XGBoost-v3", "family": "Gradient Boosting", "status": "Production candidate", "trainingWindow": "2018-2024", "validation": "Walk-forward (12 folds)", "sharpe": 1.02, "cagr": 19.4, "maxDrawdown": -15.4, "drift": "Low", "auc": 0.64, "accuracy": 0.583, "features": 84, "lastTrained": "2026-06-01", "experimentId": "exp-2041"},
    {"id": "lgbm-v2", "name": "LightGBM-v2", "family": "Gradient Boosting", "status": "Champion", "trainingWindow": "2018-2024", "validation": "Walk-forward (12 folds)", "sharpe": 0.96, "cagr": 17.8, "maxDrawdown": -16.9, "drift": "Low", "auc": 0.62, "accuracy": 0.571, "features": 84, "lastTrained": "2026-05-28", "experimentId": "exp-2033"},
    {"id": "rf-v1", "name": "Random Forest", "family": "Bagging Ensemble", "status": "Baseline", "trainingWindow": "2018-2024", "validation": "Walk-forward (12 folds)", "sharpe": 0.74, "cagr": 13.1, "maxDrawdown": -21.2, "drift": "Medium", "auc": 0.59, "accuracy": 0.552, "features": 84, "lastTrained": "2026-05-12", "experimentId": "exp-1987"},
    {"id": "logreg", "name": "Logistic Regression", "family": "Linear", "status": "Baseline", "trainingWindow": "2018-2024", "validation": "Walk-forward (12 folds)", "sharpe": 0.61, "cagr": 10.4, "maxDrawdown": -19.8, "drift": "Low", "auc": 0.57, "accuracy": 0.541, "features": 42, "lastTrained": "2026-05-12", "experimentId": "exp-1985"},
    {"id": "lstm-exp", "name": "LSTM experimental", "family": "Deep Sequence", "status": "Experimental", "trainingWindow": "2019-2024", "validation": "Walk-forward (8 folds)", "sharpe": 0.88, "cagr": 16.2, "maxDrawdown": -24.6, "drift": "High", "auc": 0.61, "accuracy": 0.566, "features": 120, "lastTrained": "2026-06-04", "experimentId": "exp-2055"},
    {"id": "mom-base", "name": "Momentum baseline", "family": "Rules", "status": "Baseline", "trainingWindow": "n/a", "validation": "Walk-forward (12 folds)", "sharpe": 0.52, "cagr": 9.1, "maxDrawdown": -27.4, "drift": "Low", "auc": 0.54, "accuracy": 0.524, "features": 3, "lastTrained": "n/a", "experimentId": "exp-0001"},
]

FEATURE_IMPORTANCE = [
    {"feature": "Momentum 20d", "importance": 0.182},
    {"feature": "Relative strength", "importance": 0.146},
    {"feature": "Volume z-score", "importance": 0.121},
    {"feature": "Volatility regime", "importance": 0.104},
    {"feature": "Earnings revision", "importance": 0.089},
    {"feature": "Options skew", "importance": 0.077},
    {"feature": "Sector breadth", "importance": 0.066},
    {"feature": "Mean reversion 5d", "importance": 0.058},
    {"feature": "Macro factor (rates)", "importance": 0.049},
    {"feature": "Liquidity score", "importance": 0.041},
]

# fallback experiment feed for when the trial registry is empty (fresh checkout)
EXPERIMENTS = [
    {"id": "exp-2041", "model": "backtest", "metric": "Sharpe 0.68", "status": "finished", "time": "2026-06-09", "tags": []},
    {"id": "exp-2033", "model": "tuning", "metric": "Sharpe 1.09", "status": "finished", "time": "2026-06-09", "tags": ["optuna"]},
    {"id": "exp-1987", "model": "backtest", "metric": "Sharpe 0.61", "status": "finished", "time": "2026-06-08", "tags": []},
]


# --- trades ---
def trades() -> list[dict]:
    r = _rng(11)
    tickers = ["NVDA", "MSFT", "AAPL", "AMZN", "TSLA", "GOOGL", "META", "AMD"]
    out: list[dict] = []
    for i in range(14):
        t = tickers[int(r.random() * len(tickers))]
        entry = 80 + r.random() * 400
        ret = (r.random() - 0.42) * 9
        ex = entry * (1 + ret / 100)
        side = "LONG" if r.random() > 0.22 else "SHORT"
        d = date(2026, 5, 28) - timedelta(days=i)
        out.append(
            {
                "id": f"T-{4200 - i}",
                "date": d.isoformat(),
                "ticker": t,
                "side": side,
                "entry": round(entry, 2),
                "exit": round(ex, 2),
                "pnl": round((ex - entry) * 100),
                "ret": round(ret, 2),
                "hold": math.ceil(r.random() * 9),
            }
        )
    return out


# --- risk ---
EXPOSURE_BY_ASSET = [
    {"name": "NVDA", "value": 18}, {"name": "MSFT", "value": 14},
    {"name": "AAPL", "value": 12}, {"name": "META", "value": 10},
    {"name": "GOOGL", "value": 9}, {"name": "AMZN", "value": 7},
    {"name": "Cash", "value": 30},
]
EXPOSURE_BY_SECTOR = [
    {"name": "Software", "value": 33}, {"name": "Semiconductors", "value": 24},
    {"name": "Hardware", "value": 12}, {"name": "E-commerce", "value": 9},
    {"name": "Cash", "value": 22},
]
RISK_BUDGET = [
    {"label": "Gross exposure", "used": 64, "limit": 100},
    {"label": "Single-name max", "used": 18, "limit": 20},
    {"label": "Sector max", "used": 33, "limit": 40},
    {"label": "Daily VaR (95%)", "used": 1.9, "limit": 2.5},
    {"label": "Beta to QQQ", "used": 0.82, "limit": 1.2},
]
RISK_FLAGS = [
    {"id": "r1", "level": "warning", "title": "Elevated volatility regime", "detail": "Realized 10-day volatility is in the 82nd percentile. Suggested position sizing reduced by 35%.", "metric": "VIX 21.4 - +18% w/w"},
    {"id": "r2", "level": "warning", "title": "Feature drift - LSTM experimental", "detail": "PSI on 'volume z-score' exceeded 0.21. Experimental model excluded from live ensemble.", "metric": "PSI 0.21"},
    {"id": "r3", "level": "critical", "title": "Drawdown threshold approaching", "detail": "Strategy drawdown at -12.8% vs -15% soft stop. De-risking protocol armed.", "metric": "-12.8% / -15.0%"},
    {"id": "r4", "level": "info", "title": "Model retrain scheduled", "detail": "XGBoost-v3 scheduled for walk-forward refit on 2026-06-15.", "metric": "in 8 days"},
]
POSITION_RULES = [
    "Kelly-fraction sizing capped at 0.5x with volatility scaling.",
    "Per-name exposure hard cap at 20% of gross.",
    "Soft drawdown stop at -15%; full de-risk at -20%.",
    "Position sizing scales inversely with realized volatility regime.",
    "No new entries when realized vol > 90th percentile.",
]


def volatility_regime() -> list[dict]:
    r = _rng(19)
    return [
        {
            "t": i,
            "vix": round(14 + math.sin(i / 4) * 5 + r.random() * 6, 2),
            "realized": round(12 + math.sin(i / 5 + 1) * 4 + r.random() * 5, 2),
        }
        for i in range(40)
    ]


# --- rag ---
RAG_DEFAULT = {
    "prompt": "Why did the model generate a BUY signal for NVDA?",
    "answer": "XGBoost-v3 issued a BUY for NVDA with 78% confidence. The decision is dominated by strong 20-day momentum and a volume spike (+2.3 sigma vs trailing mean), reinforced by positive analyst earnings revisions over the past two weeks. Relative strength versus the semiconductor peer group sits in the 88th percentile. The model projects a +2.1% five-day forward return, though it flags the signal as High risk given elevated implied volatility.",
    "sources": [
        {"title": "NVDA Q1 FY26 earnings call transcript", "type": "Earnings", "date": "2026-05-22", "snippet": "Data-center revenue grew 78% YoY; management guided above consensus on continued accelerator demand..."},
        {"title": "Sell-side estimate revisions - Semis", "type": "Research", "date": "2026-05-30", "snippet": "Consensus FY26 EPS revised +6.4% over trailing 14 days; 12 of 14 analysts raised targets..."},
        {"title": "XGBoost-v3 SHAP attribution report", "type": "Model report", "date": "2026-06-06", "snippet": "Top positive contributors: momentum_20d (+0.18), volume_z (+0.12), rel_strength (+0.11)..."},
    ],
    "signalContext": {"ticker": "NVDA", "signal": "BUY", "confidence": 78, "model": "XGBoost-v3"},
    "riskWarnings": [
        "Implied volatility in the 84th percentile - wider stop recommended.",
        "Signal is momentum-driven and may decay quickly on a regime shift.",
        "High concentration: NVDA already at 18% of gross exposure (cap 20%).",
    ],
    "confidence": 78,
}

RAG_RISKS = {
    "prompt": "What risks contradict the current signal?",
    "answer": "Several factors push against the active BUY. First, the volatility regime is elevated (realized vol in the 82nd percentile), which historically compresses momentum-strategy Sharpe. Second, NVDA already represents 18% of gross exposure against a 20% single-name cap, leaving little room to add. Third, options skew has steepened, implying the market is paying up for downside protection. The model's confidence (78%) is meaningful but not extreme, and similar setups have a 57% historical hit rate.",
    "sources": [
        {"title": "Risk layer - exposure snapshot", "type": "Model report", "date": "2026-06-07", "snippet": "NVDA 18.0% of gross - single-name cap 20% - sector (Semis) 24%..."},
        {"title": "Volatility regime monitor", "type": "Model report", "date": "2026-06-07", "snippet": "Realized 10d vol 82nd pct; suggested sizing multiplier 0.65x..."},
        {"title": "Options analytics - NVDA skew", "type": "News", "date": "2026-06-05", "snippet": "25-delta put-call skew steepened to +6.1 vol points week over week..."},
    ],
    "signalContext": {"ticker": "NVDA", "signal": "BUY", "confidence": 78, "model": "XGBoost-v3"},
    "riskWarnings": [
        "Elevated volatility regime - sizing automatically reduced 35%.",
        "Near single-name concentration cap.",
        "Steepening put skew signals hedging demand.",
    ],
    "confidence": 64,
}


def rag_response(prompt: str) -> dict:
    p = prompt.lower()
    if "risk" in p or "contradict" in p:
        return RAG_RISKS
    return {**RAG_DEFAULT, "prompt": prompt}
