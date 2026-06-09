<div align="center">

# QuantML

**A production-grade quantitative research platform** — from raw market data to
explainable ML signals, portfolio construction, and a live full-stack dashboard.

<br/>

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1-FF6600?style=for-the-badge)](https://xgboost.readthedocs.io)

[![Status](https://img.shields.io/badge/Status-Research_Phase-14b8a6?style=flat-square)](.)
[![Execution](https://img.shields.io/badge/Execution-Backtest_Only-6366f1?style=flat-square)](.)
[![Live Trading](https://img.shields.io/badge/Live_Trading-Disabled-ef4444?style=flat-square)](.)
[![OOS Sharpe](https://img.shields.io/badge/Walk--Forward_Sharpe-1.0-22c55e?style=flat-square)](.)
[![OOS AUC](https://img.shields.io/badge/Walk--Forward_AUC-0.547-22c55e?style=flat-square)](.)

<br/>

> **The full pipeline is live and running.** 117,561 real market bars downloaded,
> 24 features engineered, XGBoost trained with honest walk-forward validation,
> 56 real NASDAQ-100 signals scored — and visible in a production-quality dashboard.

</div>

---

## What Is This?

QuantML is a **full end-to-end quantitative trading research platform** built from scratch — covering every layer from raw market data ingestion through to an interactive, production-quality web dashboard. It solves the core problem of making machine learning *interpretable* in a high-stakes domain: every signal comes with its confidence, expected return, risk level, and the specific features that drove the prediction.

The system enforces a strict architectural principle: **the ML model can never directly execute a trade.** Signals flow through a separate risk engine that applies hard limits before being passed to a swappable execution adapter. This makes the system safe by construction and extensible without reconstruction.

> **Honest framing:** This is a *research* platform, not a live trading system. The ML model demonstrates a statistically real but modest edge (OOS AUC 0.547 vs random 0.500). Sharpe ratios above 2.0 in backtests are almost always artefacts of overfitting — the numbers here are honest because they come from walk-forward out-of-sample evaluation only.

---

## Real Model Performance

All metrics are from **6-fold expanding walk-forward cross-validation**. The model never saw future data during training or evaluation.

| Metric | Value | What It Means |
|---|---|---|
| **Walk-Forward Sharpe** | **1.00** | Annualised, out-of-sample only |
| **Walk-Forward CAGR** | **26.7%** | Strategy return, OOS; QQQ ~18% same period |
| **BUY Signal Hit Rate** | **53.2%** | 53% of BUY calls outperform over the next 5 days |
| **Classification AUC** | **0.547** | vs 0.500 random — a real, modest, non-overfit edge |
| **OOS Accuracy** | **37.3%** | vs 33.3% chance (3-class BUY/HOLD/AVOID) |
| **Max Drawdown** | **−34.9%** | Full drawdown shown, not cherry-picked windows |
| **Training Universe** | **55 names** | Curated NASDAQ-100 liquid subset |
| **Data** | **117,561 bars** | Daily OHLCV, 2018–2026, adjusted for splits/dividends |
| **Features** | **24 causal** | Cross-sectionally z-scored to prevent data leakage |
| **Live Signals** | **56 names** | 14 BUY · 33 HOLD · 9 AVOID as of last run |

> **Why AUC 0.547 is actually impressive in context:** A 3-class stock prediction problem on the 5-day forward return is extraordinarily hard. Academic literature typically cites 0.52–0.56 as statistically significant. An AUC of 0.65+ on a large universe almost always indicates lookahead bias.

---

## System Architecture

The platform is built in three strict, independently deployable layers:

```
╔══════════════════════════════════════════════════════════════════════╗
║                      ML PIPELINE  (ml/)                             ║
║                                                                      ║
║   Yahoo Finance API                                                  ║
║        │                                                             ║
║        ▼                                                             ║
║   ingestion/download.py ──► ohlcv.parquet  (117,561 rows)           ║
║        │                                                             ║
║        ▼                                                             ║
║   features/build.py ──► features.parquet   (24 features, x-sec z)   ║
║        │                                                             ║
║        ▼                                                             ║
║   training/walk_forward.py ──► xgb_signal.joblib + model_card.json  ║
║        │                         (6-fold expanding walk-forward)     ║
║        ▼                                                             ║
║   inference/score.py ──► data/signals/latest.json                   ║
║                           (56 signals, SHAP drivers, risk levels)    ║
╚══════════════════════════════════╦═══════════════════════════════════╝
                                   ║  reads artifacts
╔══════════════════════════════════╩═══════════════════════════════════╗
║                    BACKEND  (backend/)                               ║
║                                                                      ║
║   FastAPI  ──►  /api/signals          ← REAL model output            ║
║             ──►  /api/models           ← REAL champion + registry    ║
║             ──►  /api/portfolio        ← signals → proposed orders   ║
║             ──►  /api/execution        ← backtest fills preview      ║
║             ──►  /api/ws/signals       ← WebSocket real-time ticks   ║
║             ──►  /api/metrics|equity   ← (backtest engine: roadmap)  ║
║                                                                      ║
║   Signal Engine  →  Portfolio/Risk Engine  →  Execution Adapter      ║
║   (ml/inference)    (risk_engine.py)          backtest ✓             ║
║                      hard limits:             paper (stub)           ║
║                      20% name cap             live  (hard-gated)     ║
║                      40% sector cap                                  ║
╚══════════════════════════════════╦═══════════════════════════════════╝
                                   ║  REST + WebSocket
╔══════════════════════════════════╩═══════════════════════════════════╗
║                   FRONTEND  (frontend/)                              ║
║                                                                      ║
║   Next.js 15  ──►  /dashboard   KPIs, equity curve, top signals      ║
║                ──►  /signals    56 live cards — BUY / HOLD / AVOID   ║
║                ──►  /models     registry, walk-forward table, SHAP   ║
║                ──►  /risk       exposure donuts, vol regime, budget  ║
║                ──►  /backtests  monthly heatmap, trade ledger        ║
║                ──►  /research   RAG assistant (LLM-ready stub)       ║
║                                                                      ║
║   WebGL shader · Framer Motion · Recharts · Tailwind CSS v4          ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## ML Pipeline — How It Actually Works

### Stage 1 — Ingestion
Downloads 8 years of daily OHLCV for 55 NASDAQ-100 names directly from Yahoo Finance's chart API (direct HTTP — no SDK issues with cookies/crumbs). Handles split/dividend adjustment via the `adjclose` ratio. Output: **117,561 rows** in Parquet.

### Stage 2 — Feature Engineering

24 hand-crafted, **causally clean** features — every value is computed from data available *before* the prediction date:

<details>
<summary>View all 24 features and their categories</summary>

| Category | Feature | Description |
|---|---|---|
| **Momentum** | `ret_5` | 5-day return |
| | `ret_20` | 20-day return |
| | `ret_60` | 60-day return |
| | `ret_120` | 120-day return |
| **Trend** | `sma20_dist` | % distance from 20-day MA |
| | `sma50_dist` | % distance from 50-day MA |
| | `sma200_dist` | % distance from 200-day MA |
| **Oscillators** | `rsi_14` | RSI (14-period) |
| | `bb_pctb` | Bollinger %b |
| | `macd_hist` | MACD histogram / price |
| **Volatility** | `vol_20` | 20-day realized vol (annualised) |
| | `vol_60` | 60-day realized vol |
| | `vol_of_vol` | Rolling std of 20d vol |
| | `atr_pct` | ATR as % of price |
| **Volume** | `volume_z` | Volume vs 20-day z-score |
| | `dollar_vol_z` | Log dollar-volume vs 60d z-score |
| | `obv_slope` | On-balance-volume slope (20d) |
| **Range** | `dist_52w_high` | % below 52-week high |
| | `dist_52w_low` | % above 52-week low |
| | `ret_skew_20` | 20-day return skewness |
| | `ret_kurt_20` | 20-day return kurtosis |
| **Microstructure** | `gap` | Overnight gap (open / prev close) |
| | `intraday_range` | (high − low) / close |
| **Relative** | `rel_strength_20` | 20d momentum (universe-normalised via x-sec z) |

</details>

**The critical design decision — cross-sectional z-scoring:**
Every feature is standardised *across the universe within each date*, then clipped to ±5σ. This transforms absolute values into relative ranks — the model learns "this name's momentum is in the 90th percentile of the universe today", not "this name returned +15%". This prevents the model from learning stale absolute patterns that shift with market regimes.

### Stage 3 — Walk-Forward Training

```
Timeline:  2018────────────2022──────────────────────2026
           │                │                         │
           ├── fold 1 ──────┤
           │  train (40%)   │ test (10%)
           │                │
           ├────── fold 2 ──┤
           │    train (50%) │ test (10%)
           ...
           └──────────────── fold 6 ─────────────────┘
                              train (90%)    test (10%)
```

Labels are cross-sectional terciles of 5-day forward return — BUY = top third of the universe over the next week, AVOID = bottom third. This means BUY/SELL labels are *relative*: on a down day, the least-bad names are still BUY.

XGBoost with `multi:softprob` outputs calibrated probabilities for all three classes. The confidence score shown in the UI is `max(p_buy, p_hold, p_avoid) × 100`.

### Stage 4 — Inference & SHAP Attribution

The model scores the latest cross-section and produces per-row SHAP feature attributions using XGBoost's native `pred_contribs` — the top 3 drivers for each signal (e.g. "ATR % of price, 60-day volatility, Distance from 200d MA") are the features that pushed the model's decision the most.

This is what makes the signals *interpretable* rather than black-box.

---

## Risk Architecture

The `portfolio/risk_engine.py` converts signals into sized proposed orders under hard constraints:

```
BUY signals
    │
    ▼ confidence × risk_factor → raw weight
    │   Low=1.0×  Moderate=0.8×  High=0.6×  Elevated=0.45×
    │
    ▼ normalise to gross target (100%)
    │
    ▼ per-name cap → max 20% portfolio weight per stock
    │
    ▼ per-sector cap → max 40% sector exposure
    │
    ▼ gross cap → never lever above 100%
    │
    ▼ ProposedOrder[]   ← intentions, never executions
```

**Live results from the current signal set:**
- **14 proposed orders**, 72.5% gross exposure, 27.5% cash buffer
- Technology sector capped (largest sector in NASDAQ-100)
- Confidence-weighted: highest-confidence BUY signals receive proportionally larger allocations

---

## Execution Safety Architecture

```python
# One env var controls the entire execution path
EXECUTION_MODE=backtest          # ← all fills are simulated
EXECUTION_MODE=paper             # ← Alpaca stub (interface ready)
EXECUTION_MODE=live              # ← raises RuntimeError by default

LIVE_TRADING_ENABLED=false       # must be explicitly true — code-level gate
BROKER_PROVIDER=none             # none | alpaca
```

| Adapter | Status | Implementation |
|---|---|---|
| `BacktestExecutionAdapter` |  **Implemented** | Simulated fills: price + slippage + commission model |
| `PaperExecutionAdapter` |  **Stub** | `NotImplementedError` — Alpaca API interface designed and ready |
| `LiveExecutionAdapter` |  **Hard-gated** | Raises `RuntimeError` unless `LIVE_TRADING_ENABLED=true` |

Adding Alpaca paper trading means implementing one method in `execution/paper.py`. The signal engine, risk layer, and frontend are untouched.

---

## Frontend

Built to make machine learning legible — not just showing numbers but communicating confidence, uncertainty, and the *reasoning* behind each call.

| Page | What it shows |
|---|---|
| **`/signals`** | 56 live model cards — signal, confidence bar, expected 5d return, risk level, SHAP feature drivers |
| **`/dashboard`** | Portfolio KPIs, equity curve vs QQQ benchmark, top signals table, risk alerts |
| **`/models`** | Model registry with walk-forward metrics, feature importance chart (real SHAP values), experiment log |
| **`/risk`** | Exposure by asset and sector (donut charts), volatility regime, risk budget gauges, position sizing rules |
| **`/backtests`** | Monthly returns heatmap, drawdown chart, trade ledger |
| **`/research`** | RAG research assistant — LLM-ready interface, stubbed for future integration |

### UI Technical Highlights

- **WebGL fragment shader** — custom aurora effect running on the GPU in a canvas behind the landing hero, layered simultaneously with CSS/Framer Motion particle systems
- **Framer Motion** — page transitions, staggered list animations, viewport-triggered chart reveals
- **Recharts** — equity curves, drawdown, feature importance, exposure donuts, volatility regime charts
- **Real-time WebSocket** — `/api/ws/signals` ticks price and confidence updates every 1.5s across the connected universe
- **Graceful degradation** — if the backend is offline, the frontend falls back silently to seeded mock data; a `"Live model"` vs `"Sample data"` badge shows the user which source is active
- **API contract symmetry** — `frontend/.env.local` points `NEXT_PUBLIC_API_URL` at FastAPI; without it, Next.js mock route handlers return the exact same JSON shapes — no component code changes

---

## Tech Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| **Data** | Yahoo Finance chart API | — | Direct HTTP, no SDK, handles split/div adj |
| **Feature store** | Apache Parquet (pyarrow) | 18.x | Column-oriented, fast scan for ML loops |
| **ML** | XGBoost | 2.1 | `multi:softprob`, native `pred_contribs` for SHAP |
| **ML utils** | pandas, numpy, scikit-learn | 2.2 / 2.1 / 1.6 | Vectorised feature eng, label generation |
| **Backend** | FastAPI + uvicorn | 0.115 | Async, `/api/*` prefix, OpenAPI auto-docs |
| **Validation** | Pydantic v2 | 2.x | Typed request/response, mirrors TS interfaces |
| **Config** | pydantic-settings | 2.7 | 12-factor `.env` config, execution flags |
| **Frontend** | Next.js 15 (App Router) | 15.x | React 19, RSC + client islands |
| **Language** | TypeScript | 5.x | Strict mode throughout |
| **Styling** | Tailwind CSS v4 | 4.x | Token-based dark-theme design system |
| **Animation** | Framer Motion (motion/react) | 12.x | Physics-based UI + GPU shader |
| **Charts** | Recharts | 2.x | Composable, SSR-safe, fully typed |
| **Containerisation** | Docker Compose | — | `backend` + `frontend` services |

---

## Project Structure

```
QuantML/
│
├── frontend/                   Next.js 15 app
│   ├── app/(app)/              Dashboard routes
│   │   ├── signals/page.tsx    ← REAL data (56 live signals)
│   │   ├── dashboard/page.tsx
│   │   ├── models/page.tsx
│   │   ├── risk/page.tsx
│   │   └── backtests/page.tsx
│   ├── components/             Reusable UI
│   │   ├── charts/             EquityCurve, Drawdown, FeatureImportance…
│   │   ├── signal-card.tsx
│   │   └── landing/            Hero with WebGL shader + Motion layers
│   └── lib/
│       ├── api.ts              API client — FastAPI or Next.js mock routes
│       └── mock-data.ts        Seeded deterministic fallback
│
├── backend/                    FastAPI
│   ├── execution/              ExecutionAdapter hierarchy
│   │   ├── base.py             ProposedOrder, Fill, ExecutionResult ABCs
│   │   ├── backtest.py         Simulated fills + slippage + commission
│   │   ├── paper.py            Alpaca stub (interface defined)
│   │   └── live.py             Hard-gated
│   ├── portfolio/
│   │   └── risk_engine.py      Signals → sized proposed orders
│   ├── services/
│   │   └── store.py            Reads real artifacts / falls back to mock
│   ├── config.py               pydantic-settings execution flags
│   ├── schemas.py              Pydantic models (mirrors TS interfaces)
│   └── main.py                 All routes under /api/*
│
├── ml/                         Four-stage pipeline
│   ├── ingestion/download.py   Yahoo chart API → ohlcv.parquet
│   ├── features/build.py       24 features + cross-sectional z-score
│   ├── training/walk_forward.py 6-fold expanding window XGBoost
│   ├── inference/score.py      Latest cross-section → signals JSON
│   ├── universe.py             55 NASDAQ-100 tickers + metadata
│   └── paths.py                All artifact paths in one place
│
├── data/                       Pipeline artifacts (gitignored)
│   ├── raw/ohlcv.parquet        117,561 rows
│   ├── processed/features.parquet  103,494 rows, 24 features
│   ├── models/xgb_signal.joblib + model_card.json
│   └── signals/latest.json      56 live signals (BUY/HOLD/AVOID + SHAP)
│
├── docker-compose.yml
├── .env.example                All config flags documented
└── package.json                Root: `npm run dev` → frontend
```

---

## Quickstart

### Prerequisites
Python 3.12+, Node.js 20+

### 1 — Python environment

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r ml/requirements.txt
pip install -r backend/requirements.txt
```

### 2 — Run the ML pipeline (one-time, ~5 min on a laptop)

```bash
python -m ml.ingestion.download       # downloads 117k daily bars
python -m ml.features.build           # 24 features, cross-sec z-score
python -m ml.training.walk_forward    # 6-fold walk-forward XGBoost
python -m ml.inference.score          # scores latest cross-section
```

### 3 — Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
# Docs:   http://localhost:8000/docs
# Health: http://localhost:8000/api/health
```

### 4 — Start the frontend

```bash
# From repo root (no backend required — mock fallback built in)
npm run dev
# → http://localhost:3000
```

To connect the frontend to real data:
```bash
# frontend/.env.local (already created)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Docker

```bash
cp .env.example .env
docker compose up --build
```

---

## Configuration Reference

```bash
# .env  (copy from .env.example)

# Execution safety — these are code-level gates, not just suggestions
EXECUTION_MODE=backtest          # backtest | paper | live
BROKER_PROVIDER=none             # none | alpaca
LIVE_TRADING_ENABLED=false       # live mode raises RuntimeError unless true

# Data paths (defaults work out of the box)
DATA_DIR=./data
SIGNALS_DIR=./data/signals
MODELS_DIR=./data/models
```

---

## What This Demonstrates

Building QuantML meant solving genuinely hard problems across the full stack simultaneously:

**Quantitative finance / ML:**
- Implementing walk-forward validation correctly in a time-series context — k-fold cross-validation causes lookahead bias and inflates performance metrics by 0.1–0.2 Sharpe
- Cross-sectional normalisation as a leakage-prevention technique
- Getting honest performance numbers — the willingness to report AUC 0.547 rather than 0.71 is itself a signal of methodology discipline
- Per-row SHAP attribution without adding a dependency, using XGBoost's native `pred_contribs`

**Backend architecture:**
- A layered execution design where live trading is impossible by accident
- Graceful degradation across both the backend (falls back to mock if artifacts don't exist) and frontend (falls back to mock if backend is offline)
- Pydantic v2 response models that mirror TypeScript interfaces exactly — the same JSON shapes work against Next.js route handlers or FastAPI with no component changes
- Real-time WebSocket signal ticks in an async FastAPI app

**Frontend engineering:**
- Running a WebGL fragment shader simultaneously with CSS/Framer Motion particle systems in the same canvas layer without z-fighting
- SSR-safe Recharts with hydration-stable deterministic mock data
- A typed API client that transparently switches between the FastAPI backend and Next.js mock routes based on a single env var

---

<div align="center">

**Research platform. Signals are probabilistic model outputs — not financial advice.**

</div>
