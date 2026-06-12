<div align="center">

# QuantML

**A production-grade quantitative research platform** — from raw market data to
explainable ML signals, portfolio construction, and a live full-stack dashboard.

<br/>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![XGBoost](https://img.shields.io/badge/XGBoost-2.1-FF6600?style=for-the-badge)](https://xgboost.readthedocs.io)

[![Status](https://img.shields.io/badge/Status-Research_Phase-14b8a6?style=flat-square)](.)
[![Execution](https://img.shields.io/badge/Execution-Backtest_Only-6366f1?style=flat-square)](.)
[![Live Trading](https://img.shields.io/badge/Live_Trading-Disabled-ef4444?style=flat-square)](.)
[![Tests](https://img.shields.io/badge/tests-68_passing-22c55e?style=flat-square)](.)
[![Signal Sharpe](https://img.shields.io/badge/Signal_Sharpe-1.0-22c55e?style=flat-square)](.)
[![Net-of-cost Sharpe](https://img.shields.io/badge/Net--of--cost_Sharpe-0.68-eab308?style=flat-square)](.)
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

## Performance — Two Honest Lenses

Two numbers get reported here, because they answer two different questions.
Conflating them is exactly how backtests lie.

### 1. Signal quality — does the model rank names better than chance?

Measured on the raw BUY basket: equal-weighted, non-overlapping 5-day forward
returns, **no costs, no position sizing**. This isolates the model's predictive
edge. All from 6-fold expanding walk-forward cross-validation — no fold ever sees
its own future.

| Metric | Value | What it means |
|---|---|---|
| **Walk-forward Sharpe** | **1.00** | annualised, out-of-sample only (frictionless basket) |
| **Classification AUC** | **0.547** | vs 0.500 random — a real, modest, non-overfit edge |
| **OOS accuracy** | **37.3%** | vs 33.3% chance (3-class BUY/HOLD/AVOID) |
| **BUY hit rate** | **53.2%** | share of BUY calls with a positive 5-day return |
| **Basket max drawdown** | **−34.9%** | full history, not a cherry-picked window |

> A 3-class stock-direction problem on the 5-day forward return is genuinely hard.
> The literature treats AUC 0.52–0.56 as statistically significant; an AUC of 0.65+
> on a large universe almost always means lookahead bias has crept in.

### 2. Net-of-cost backtest — would it have made money after frictions?

The same out-of-sample signals, run through the **live risk engine** (confidence/
volatility sizing, 20% name cap, 40% sector cap, 100% gross cap) and a
**transaction-cost model** (5 bps commission + 8 bps slippage = 13 bps round-trip,
charged on turnover). This is the honest, deployable number — the default config,
reproducible with `cd backend && python -m backtesting.engine`.

| Metric | Strategy | QQQ (buy & hold) |
|---|---|---|
| **CAGR** | **13.98%** | 15.68% |
| **Total return** | **78.4%** | 90.5% |
| **Sharpe** | **0.68** | — |
| **Sortino** | 0.95 | — |
| **Max drawdown** | −37.4% | — |
| **Volatility (ann.)** | 23.3% | — |
| **Win rate / profit factor** | 58.8% / 1.47 | — |
| **Beta to QQQ** | 0.94 | — |
| **Trades** | 1,524 over 224 weekly rebalances | — |

> Window 2021-12 → 2026-05 (the out-of-sample span of the walk-forward folds).

**Why the Sharpe drops from 1.00 to 0.68 — and why that's the whole point.** The
signal Sharpe is an idealised, frictionless equal-weight basket (its paper CAGR is
26.7%). The backtest then *pays for realism*: transaction costs on ~3,800%/yr
turnover, position sizing that holds cash when conviction is low, and the
name/sector caps — which pulls the deployable CAGR down to ~14%. Reporting both,
and showing the gap rather than hiding it, **is** the methodology. A backtest that
matched the frictionless number would be the red flag.

**Universe & data:** 55 curated NASDAQ-100 names · 117,561 daily OHLCV bars
(2018–2026, split/dividend adjusted) · 24 causal, cross-sectionally z-scored
features · 56 live signals on the latest cross-section (14 BUY · 33 HOLD · 9 AVOID).

---

## Model Quality — Does It Beat the Baselines?

A Sharpe of 1.0 means nothing until you ask "compared to *what?*" So every model
below runs through the **identical** walk-forward folds, features and labels — only
the estimator changes (`python -m ml.training.baselines`).

| Model | Sharpe | CAGR | AUC | BUY hit | Verdict |
|---|---|---|---|---|---|
| **XGBoost-v3** (champion) | **1.00** | 26.7% | 0.547 | 53.2% | shipped |
| Random Forest | 0.99 | 27.4% | 0.552 | 53.1% | statistically tied |
| Cross-sectional Momentum | 0.89 | 21.6% | 0.507 | 53.9% | the "do you need ML?" control |
| Logistic Regression | 0.85 | 21.9% | 0.547 | 52.4% | linear floor |

The honest read: **the two tree ensembles beat momentum and the linear model by
~0.1 Sharpe — a real edge — but XGBoost and Random Forest are a dead heat** (+0.01
is noise). XGBoost ships because of its calibrated class probabilities and native
SHAP attributions, not because it dominates. A table that showed XGBoost crushing
everything would be the thing to distrust.

### Where the edge actually lives

The headline Sharpe hides a lot. Broken down by year and by market regime
(`python -m ml.research.regime`), the OOS BUY basket looks like this:

| Year | Sharpe | | Regime | Sharpe |
|---|---|---|---|---|
| 2022 (QQQ −33%) | **−0.75** | | Bull (QQQ > 200d) | 1.32 |
| 2023 (QQQ +56%) | 2.80 | | Bear (QQQ < 200d) | 0.60 |
| 2024 | 1.05 | | | |
| 2025 | 1.52 | | | |

It **lost money in 2022** and earns most of its keep in trending bull markets. That
is exactly the kind of thing a backtest should disclose, not bury under an average.

### Hyperparameter tuning & feature sensitivity

**Optuna search** (30 trials, walk-forward objective, logged to the anti-overfit registry):
- Default config: Sharpe 1.00
- **Best tuned params: Sharpe 1.19** (n_estimators=350, max_depth=5, learning_rate=0.088, etc.)
- **DSR 1.0** — survives the multiple-testing correction; the improvement is real, not luck

**Feature ablation** (drop each group, measure OOS Sharpe):
- Dropping **Relative Strength** → Sharpe −0.11 (critical carrier of edge)
- Dropping **Trend, Oscillators, or Range/Extremes** → Sharpe +0.09 to +0.13 (actually hurt when included — overfitting to junk)
- Earnings-inspired features: +0.01 Sharpe only (not worth shipping)
- Conclusion: the **24-feature set is overfit**. Relative Strength (momentum) alone is the core signal; the rest add noise.

This kind of honest weakness — admitting the full feature set hurts performance — is the mark of real work, not marketing.

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
║             ──►  /api/backtests        ← REAL walk-forward engine    ║
║             ──►  /api/metrics|equity   ← REAL net-of-cost backtest   ║
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

## Testing & CI

**68 deterministic tests.** No network, no model retraining, and no dependence on
the gitignored `data/` artifacts — every test builds its own seeded fixtures or
exercises the same mock fallback the API uses on a cold checkout. They pin down the
parts that actually have to be correct:

| Area | What's asserted |
|---|---|
| **Cost model** | commission + slippage charged on turnover; turnover accounting |
| **Performance metrics** | Sharpe / drawdown / CAGR against hand-checked closed forms |
| **Risk engine** | 20% name cap, 40% sector cap, 100% gross cap, BUY-only sizing |
| **Labels** | cross-sectional terciles, concurrency-based sample weights, triple-barrier |
| **Trial registry** | append-only log; PSR rises with track record; DSR is stricter than PSR |
| **Execution** | backtest fills include slippage; **live mode blocked unless explicitly enabled** |
| **Features** | the forward target is genuinely forward; cross-sectional z-score is standardised |
| **API** | every endpoint's shape + the live-trading-disabled safety contract |

```bash
pip install -r requirements-dev.txt
ruff check ml backend tests     # lint + import order
pytest                          # 68 passed
```

GitHub Actions runs `ruff` + `pytest` (Python 3.11) and a production `next build`
(which also runs the TypeScript and ESLint checks) on every push and PR —
see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Frontend

Built to make machine learning legible — not just showing numbers but communicating confidence, uncertainty, and the *reasoning* behind each call.

| Page | What it shows |
|---|---|
| **`/signals`** | 56 live model cards — signal, confidence bar, expected 5d return, risk level, SHAP feature drivers |
| **`/dashboard`** | Portfolio KPIs, equity curve vs QQQ benchmark, top signals table, risk alerts |
| **`/models`** | Model registry with walk-forward metrics, feature importance chart (real SHAP values), experiment log |
| **`/risk`** | Exposure by asset and sector (donut charts), volatility regime, risk budget gauges, position sizing rules |
| **`/backtests`** | Live walk-forward engine — equity curve, drawdown, monthly heatmap, trade ledger; rerun with custom costs/rebalance |
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
| **Testing** | pytest + ruff | 8.x / 0.8 | 68 offline tests, lint + import order, CI-gated |
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
├── ml/                         ML pipeline + research bookkeeping
│   ├── ingestion/download.py   Yahoo chart API → ohlcv.parquet
│   ├── features/build.py       24 features + cross-sectional z-score
│   ├── labels/                 explicit labels: outperformance + triple-barrier
│   ├── training/walk_forward.py 6-fold expanding window XGBoost
│   ├── inference/score.py      Latest cross-section → signals JSON
│   ├── research/               trial registry + deflated Sharpe (anti-overfit)
│   ├── universe.py             55 NASDAQ-100 tickers + metadata
│   └── paths.py                All artifact paths in one place
│
├── tests/                      68 pytest tests (costs, metrics, risk, labels,
│                               registry, execution, features, API)
├── .github/workflows/ci.yml    ruff + pytest + next build on every push/PR
├── pyproject.toml              pytest + ruff config
├── requirements-dev.txt        pytest, httpx, ruff
│
├── data/                       Pipeline artifacts (gitignored)
│   ├── raw/ohlcv.parquet        117,561 rows
│   ├── processed/features.parquet  24 features, cross-sectionally z-scored
│   ├── models/xgb_signal.joblib + model_card.json
│   ├── backtests/latest.json    net-of-cost walk-forward result
│   └── signals/latest.json      56 live signals (BUY/HOLD/AVOID + SHAP)
│
├── docker-compose.yml
├── .env.example                All config flags documented
└── package.json                Root: `npm run dev` → frontend
```

---

## Quickstart

### Prerequisites
Python 3.11+, Node.js 20+

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

### 5 — Run the backtest and the tests

```bash
cd backend && python -m backtesting.engine   # net-of-cost walk-forward backtest
cd .. && pip install -r requirements-dev.txt
ruff check ml backend tests                   # lint
pytest                                         # 68 passed
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
- Reporting both the frictionless signal Sharpe (1.0) and the net-of-cost backtest Sharpe (0.68), and treating the gap as the result rather than hiding it
- Multiple-testing correction via the Deflated Sharpe Ratio, backed by an append-only trial registry — the standard defence against backtest overfitting
- Per-row SHAP attribution without adding a dependency, using XGBoost's native `pred_contribs`

**Backend architecture:**
- A layered execution design where live trading is impossible by accident
- Graceful degradation across both the backend (falls back to mock if artifacts don't exist) and frontend (falls back to mock if backend is offline)
- Pydantic v2 response models that mirror TypeScript interfaces exactly — the same JSON shapes work against Next.js route handlers or FastAPI with no component changes
- Real-time WebSocket signal ticks in an async FastAPI app
- A 68-test suite plus CI that runs entirely offline by design — tests build their own seeded fixtures and exercise the same mock fallback the services use on a cold checkout, so the safety gates (live-trading lock, risk caps) are regression-tested on every push

**Frontend engineering:**
- Running a WebGL fragment shader simultaneously with CSS/Framer Motion particle systems in the same canvas layer without z-fighting
- SSR-safe Recharts with hydration-stable deterministic mock data
- A typed API client that transparently switches between the FastAPI backend and Next.js mock routes based on a single env var

---

<div align="center">

**Research platform. Signals are probabilistic model outputs — not financial advice.**

</div>
