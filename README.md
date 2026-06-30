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
[![Tests](https://img.shields.io/badge/tests-137_passing-22c55e?style=flat-square)](.)
[![Signal Sharpe](https://img.shields.io/badge/Signal_Sharpe-1.19-22c55e?style=flat-square)](.)
[![Net-of-cost Sharpe](https://img.shields.io/badge/Net--of--cost_Sharpe-0.88-eab308?style=flat-square)](.)
[![OOS AUC](https://img.shields.io/badge/Walk--Forward_AUC-0.540-22c55e?style=flat-square)](.)

<br/>

> The full pipeline runs end to end: 117,561 daily market bars downloaded, 24 features
> engineered, an Optuna-tuned XGBoost trained with walk-forward validation, and 56
> NASDAQ-100 signals scored, all visible in the dashboard.

</div>

---

## What Is This?

QuantML is an end-to-end quantitative trading research platform covering every layer from raw market data ingestion to an interactive web dashboard. The aim is to keep the machine learning interpretable: every signal carries its confidence, expected return, risk level, and the specific features that drove the prediction.

One rule runs through the system: the ML model never executes a trade directly. Signals pass through a separate risk engine that applies hard limits before reaching a swappable execution adapter, so turning on paper or live execution later is a configuration change rather than a rewrite.

> **Scope:** this is a research platform, not a live trading system. The model shows a statistically real but modest edge (OOS AUC 0.540 vs 0.500 random). Backtest Sharpe ratios above 2.0 are almost always overfitting artefacts; the numbers here come from walk-forward out-of-sample evaluation only.

---

## Performance — Two Lenses

Two numbers are reported here because they answer two different questions, and mixing
them up is how backtests end up looking better than they really are.

### 1. Signal quality — does the model rank names better than chance?

Measured on the raw BUY basket: equal-weighted, non-overlapping 5-day forward
returns, **no costs, no position sizing**. This isolates the model's predictive
edge. All from 6-fold expanding walk-forward cross-validation — no fold ever sees
its own future.

| Metric | Value | What it means |
|---|---|---|
| **Walk-forward Sharpe** | **1.19** | annualised, out-of-sample only (frictionless basket) |
| **Classification AUC** | **0.540** | vs 0.500 random — a real, modest, non-overfit edge |
| **OOS accuracy** | **36.6%** | vs 33.3% chance (3-class BUY/HOLD/AVOID) |
| **BUY hit rate** | **52.8%** | share of BUY calls with a positive 5-day return |
| **Basket max drawdown** | **−29.3%** | full history, not a cherry-picked window |

> A 3-class stock-direction problem on the 5-day forward return is genuinely hard.
> The literature treats AUC 0.52–0.56 as statistically significant; an AUC of 0.65+
> on a large universe almost always means lookahead bias has crept in.
>
> One trade-off from the Optuna tuning: it lifted the basket Sharpe (1.00 to 1.19) and
> cut drawdown, but the pointwise classification metrics nudged down (AUC 0.547 to 0.540,
> accuracy 37.3% to 36.6%). The tuning objective was risk-adjusted basket return, not raw
> class accuracy, so the two move in opposite directions.

### 2. Net-of-cost backtest — would it have made money after frictions?

The same out-of-sample signals, run through the **live risk engine** (confidence/
volatility sizing, 20% name cap, 40% sector cap, 100% gross cap) and a
**transaction-cost model** (5 bps commission + 8 bps slippage = 13 bps round-trip,
charged on turnover). This is the honest, deployable number — the default config,
reproducible with `cd backend && python -m backtesting.engine`.

| Metric | Strategy | QQQ (buy & hold) |
|---|---|---|
| **CAGR** | **18.50%** | 15.68% |
| **Total return** | **112.0%** | 90.5% |
| **Sharpe** | **0.88** | — |
| **Sortino** | 1.24 | — |
| **Max drawdown** | −29.7% | — |
| **Volatility (ann.)** | 22.0% | — |
| **Win rate / profit factor** | 57.8% / 1.52 | — |
| **Beta to QQQ** | 0.89 | — |
| **Trades** | 1,878 over 224 weekly rebalances | — |

> Window 2021-12 → 2026-05 (the out-of-sample span of the walk-forward folds).

**Why the Sharpe drops from 1.19 to 0.88.** The signal Sharpe is an idealised,
frictionless equal-weight basket (paper CAGR 31.2%). The backtest then pays for realism:
transaction costs on ~4,700%/yr turnover, position sizing that holds cash when conviction
is low, and the name/sector caps, which pull the deployable CAGR down to ~18.5%. Both
numbers are reported, and the gap between them is what matters: a backtest that matched the
frictionless number would be a sign of overfitting.

> Net of costs the strategy edges QQQ (18.5% vs 15.7% CAGR, 112% vs 90% total return),
> but at a 0.89 beta over a tech-heavy bull run. Read it as a tech-beta basket that paid
> for itself after frictions, not as market-neutral alpha.

**Universe & data:** 55 curated NASDAQ-100 names · 117,561 daily OHLCV bars
(2018–2026, split/dividend adjusted) · 24 causal, cross-sectionally z-scored
features · 56 live signals on the latest cross-section (18 BUY · 25 HOLD · 13 AVOID).

---

## Model Quality — Baselines

A Sharpe of 1.0 means little without a baseline. Every model below runs through the
identical walk-forward folds, features, and labels; only the estimator changes
(`python -m ml.training.baselines`).

| Model | Sharpe | CAGR | AUC | BUY hit | Verdict |
|---|---|---|---|---|---|
| **XGBoost-v3** (champion, tuned) | **1.19** | 31.2% | 0.540 | 52.8% | shipped |
| Random Forest | 0.99 | 27.4% | 0.552 | 53.1% | runner-up (untuned) |
| Cross-sectional Momentum | 0.89 | 21.6% | 0.507 | 53.9% | the "do you need ML?" control |
| Logistic Regression | 0.85 | 21.9% | 0.547 | 52.4% | linear floor |

The tuned XGBoost leads Random Forest by about 0.2 Sharpe, but that gap needs context.
Only XGBoost has been through the Optuna walk-forward search; the other three run at
sensible defaults, so part of the 0.2 is tuning effort rather than a model-family
advantage, and an equally-tuned Random Forest would likely close much of it. Random
Forest also posts the higher AUC (0.552 vs 0.540): XGBoost's edge is in risk-adjusted
basket return, not raw classification. It ships for that, plus its calibrated
probabilities and native SHAP attributions, not because it wins on every axis.

### Where the edge comes from

The headline Sharpe hides a lot. Broken down by year and by market regime
(`python -m ml.research.regime`), the OOS BUY basket looks like this:

| Year | Sharpe | | Regime | Sharpe |
|---|---|---|---|---|
| 2022 (QQQ −33%) | **−0.64** | | Bull (QQQ > 200d) | 1.57 |
| 2023 (QQQ +56%) | 2.82 | | Bear (QQQ < 200d) | 0.73 |
| 2024 | 1.38 | | | |
| 2025 | 1.69 | | | |

It lost money in 2022 and earns most of its keep in trending bull markets, the kind of
breakdown a backtest should show rather than hide behind an average.

### Hyperparameter tuning & feature sensitivity

**Optuna search** (30 trials, walk-forward objective, logged to the anti-overfit registry):
- Prior hand-picked config: Sharpe 1.00
- **Tuned params — now the shipped champion: Sharpe 1.19** (n_estimators=350, max_depth=5, learning_rate=0.088, etc.)
- **DSR ~1.0** — survives the multiple-testing correction across the 30 trials; the improvement is real, not luck

**Feature ablation** (drop each group, measure OOS Sharpe; full set = 1.19):
- Dropping **Volatility** → Sharpe −0.27 (the single biggest carrier of edge)
- Dropping **Momentum** → −0.19
- Dropping **Volume** or **Relative Strength** → −0.13 each
- Dropping Trend / Oscillators / Range / Microstructure → −0.03 to −0.07 (small but still negative)
- Earnings-inspired features: 1.19 → 0.92 (−0.27) — actively hurt, kept out of production
- Conclusion: under the tuned model **every feature group now earns its place** — dropping any one lowers OOS Sharpe, with Volatility and Momentum carrying the most weight.

This reverses an earlier finding. The previous, un-tuned champion looked overfit:
several feature groups appeared to help when removed. Re-running the same ablation on the
tuned model overturns that. Tuning got the model to use the full 24-feature set coherently,
and now no group can be dropped without cost. The earlier "the feature set is overfit"
claim was an artifact of the weaker model, corrected here rather than left in place.

---

## Model Validation & Robustness

A Sharpe from one walk-forward is a single data point. These six studies stress-test the
model the way live trading would, rather than the way a backtest flatters it. Each is
reproducible (`python -m ml.research.<name>`), offline-tested, and served at
`/api/validation` (rendered on the Validation dashboard page).

### 1. Live-cadence (anchored weekly) walk-forward

Refits **every week** on only the data available at that moment — with an explicit
5-day **label purge** so a forward return that hasn't closed can never leak into
training — and scores the next cross-section once its return is realised. 323 weeks.

| Metric | 6-fold baseline | Weekly rolling |
|---|---|---|
| **Sharpe** | 1.19 | **1.15** |
| AUC | 0.540 | 0.533 |
| Accuracy | 36.6% | 36.5% |
| Weekly hit rate | — | 58.8% |

The edge largely survives realistic weekly retraining; the 0.04 Sharpe gap is the cost of
the live cadence, not a collapse. This is the closest thing to a live dry-run the backtest
can offer.

### 2. Training-window sensitivity

The same anchored scheme at 2/3/4/5-year and expanding look-backs, all aligned to the
**same 61 evaluation weeks** so the comparison is apples-to-apples, reporting annualised
dispersion next to Sharpe (a peak Sharpe on a jumpy series isn't what you'd deploy).

| Look-back | Sharpe | CAGR | Volatility | Hit rate |
|---|---|---|---|---|
| 2y | 1.46 | 39.6% | 25.1% | 61% |
| 3y | 1.75 | 47.3% | **23.8%** | 67% |
| **4y** | **1.90** | 53.7% | 24.3% | 62% |
| 5y | 1.66 | 46.5% | 25.0% | 64% |
| expanding | 1.77 | 49.0% | 24.3% | 67% |

A 4-year window is the risk-adjusted sweet spot, 3-year the steadiest; 2 years is too
short and 5y/expanding don't improve on 4y, so the current "expanding" default isn't
optimal over this span. (Levels sit above the full-history headline because the aligned
window only covers the recent, bullish 2023+ period; the ranking is the result here, not
the absolute Sharpe.)

### 3. Regime-specialised models

Separate bull/bear models routed by the 200-day-SMA regime, vs the general model, on the
same folds, shipping the ensemble only if it actually wins.

- General 1.19 vs regime ensemble 0.95: the ensemble does not win overall, so the general
  model stays champion (the bear specialist trains on too thin a sample to be reliable).
- It did soften the 2022 bear: −0.50 vs the general model's −0.77. Regime routing helps
  where the model is weakest, at a cost to the average.

### 4. Out-of-distribution test

Train on everything before 2023, **freeze**, and evaluate untouched on 2023+ (47,872
rows) — a hard regime break (rate hikes, the AI boom), the way a live model runs between
retrains.

- Sharpe 1.89, AUC 0.540 on the unseen era: no degradation vs in-sample AUC.
- Era drift OK (max feature PSI 0.023): cross-sectional z-scoring kept the features
  in-distribution across the regime shift, which is why it generalises. The high Sharpe
  also reflects a favourable bull regime, so read this as held its edge, not found alpha.

### 5. Confidence-weighted sizing & probability calibration

The model emits a probability per class, so two questions before trusting it with size:
does sizing BUYs by conviction (`p_buy`) beat equal-weighting, and are the probabilities
*calibrated*?

- Conviction-weighted Sharpe 1.21 vs equal-weight 1.19: a small but real lift from leaning
  into the high-conviction names.
- Brier 0.227, ECE 4.3%: the BUY probabilities are well-calibrated, so a 60%-confidence
  call lands in the top tercile about 60% of the time, which is what makes sizing by
  confidence reasonable.

### 6. Retrain cadence ("online learning")

True incremental learning doesn't fit boosted trees cleanly, so the live-relevant question
is cadence: you predict every week regardless, but how often must you *refit*? Holding the
weekly (leakage-purged) prediction schedule fixed and varying only the refit frequency:

| Cadence | Refits | Sharpe | Compute |
|---|---|---|---|
| weekly | 76 | 1.50 | 746s |
| biweekly | 38 | **1.67** | 323s |
| **monthly** | 19 | 1.63 | 153s |
| quarterly | 7 | 1.44 | 59s |

More frequent isn't better. Monthly refits keep the full edge at about 5x less compute than
weekly (which mildly overfits recent noise), and only quarterly starts to lag. For a live
deployment that means retraining monthly, not nightly. (Same caveat as the window sweep: the
aligned window covers the recent bull period, so levels run above the full-history headline;
the cadence ranking is the result.)

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
║   (ml/inference)    (risk_engine.py)          backtest (active)      ║
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

**Cross-sectional z-scoring.** Every feature is standardised across the universe within each date, then clipped to ±5σ. This turns absolute values into relative ranks: the model learns "this name's momentum is in the 90th percentile of the universe today", not "this name returned +15%". It keeps the model from learning stale absolute patterns that shift with market regimes.

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
- **18 proposed orders**, 84.8% gross exposure, 15.2% cash buffer
- Technology sector capped at 40% (largest sector in NASDAQ-100)
- Confidence-weighted: highest-confidence BUY signals receive proportionally larger allocations

---

## Execution Safety Architecture

```python
# One env var controls the entire execution path
EXECUTION_MODE=backtest          # ← all fills are simulated
EXECUTION_MODE=paper             # ← Alpaca paper trading (implemented)
EXECUTION_MODE=live              # ← raises RuntimeError by default

LIVE_TRADING_ENABLED=false       # must be explicitly true — code-level gate
BROKER_PROVIDER=none             # none | alpaca
```

| Adapter | Status | Implementation |
|---|---|---|
| `BacktestExecutionAdapter` |  **Implemented** | Simulated fills: price + slippage + commission model |
| `PaperExecutionAdapter` |  **Implemented** | Notional market orders to the Alpaca paper API — env-gated, offline-tested |
| `LiveExecutionAdapter` |  **Hard-gated** | Raises `RuntimeError` unless `LIVE_TRADING_ENABLED=true` |

Paper trading is wired: set `EXECUTION_MODE=paper`, `BROKER_PROVIDER=alpaca`, and your
`ALPACA_API_KEY` / `ALPACA_API_SECRET`, and the same proposed orders flow to the Alpaca
paper account — the signal engine, risk layer, and frontend are untouched. Live trading
stays hard-gated and unimplemented by design until the live risk controls land.

---

## Testing & CI

**137 deterministic tests.** No network, no model retraining, and no dependence on
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
pytest                          # 137 passed
```

GitHub Actions runs `ruff` + `pytest` (Python 3.11) and a production `next build`
(which also runs the TypeScript and ESLint checks) on every push and PR —
see [`.github/workflows/ci.yml`](.github/workflows/ci.yml).

---

## Production Hardening (MLOps)

The research is only trustworthy if the system that produces it is. This layer adds the
operational pieces most portfolio projects skip:

- **Data-quality gates** (`ml/validation.py`) — every artifact is checked for schema,
  row count, finite values and staleness *before* anything consumes it; a critical
  failure raises and blocks promotion, so the pipeline never trains or scores on bad data.
- **Feature-drift monitoring** (`ml/research/drift.py`) — per-feature **Population
  Stability Index** of the latest cross-section vs the historical reference window, graded
  OK / WARN / ALERT, which is how you tell whether the model is still operating in-domain.
- **Pipeline orchestrator** (`ml/pipeline.py`) — one entry point runs the staged graph
  `ingest → features → validate → train → score → drift`, with the data-quality gate wired
  *between* feature-build and training, structured logging, and stage selection
  (`--start`, `--only`, `--dry-run`) for a cheap daily path vs. a full weekly retrain.
- **Scheduled cadence** ([`pipeline.yml`](.github/workflows/pipeline.yml)) — a cron
  workflow runs the daily score/drift path after the US close; a real run is gated on the
  data feed and Alpaca secrets.
- **Monitoring endpoint** — `GET /api/monitoring` serves the latest data-health report and
  drift status for the dashboard, degrading cleanly to nulls before the pipeline has run.
- **Model registry** (`ml/registry.py`) — every trained champion is versioned, and a
  promotion is only allowed once the **Deflated Sharpe Ratio** clears the gate, so a lucky
  in-sample run can't quietly take over. `rollback` restores the previous champion in one
  command; the version history shows on the Models page.
- **Observability** — a dependency-free Prometheus **`/metrics`** endpoint (request counters,
  per-route latency, and live model/drift/data-quality gauges read off the artifacts), plus
  request-tracing middleware that stamps every response with an `X-Request-ID`.

```bash
python -m ml.pipeline --dry-run        # print the stage plan
python -m ml.pipeline --only validate  # run just the data-quality gate
python -m ml.research.drift            # compute feature-drift PSI report
python -m ml.registry                  # show the versioned model registry
curl localhost:8000/metrics            # Prometheus scrape
```

---

## Frontend

The dashboard is built to make the model legible: it shows not just the numbers but the confidence, uncertainty, and reasoning behind each call.

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
| **Testing** | pytest + ruff | 8.x / 0.8 | 137 offline tests, lint + import order, CI-gated |
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
│   ├── research/               trial registry, regime, ablation, drift (PSI)
│   ├── validation.py           Data-quality gates (block promotion on bad data)
│   ├── pipeline.py             Staged orchestrator (ingest→…→drift) + data gate
│   ├── universe.py             55 NASDAQ-100 tickers + metadata
│   └── paths.py                All artifact paths in one place
│
├── tests/                      137 pytest tests (costs, metrics, risk, labels,
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
pytest                                         # 137 passed
```

### Docker — the whole stack, one command

```bash
docker compose up --build
# dashboard → http://localhost:3000 · API → http://localhost:8000 (/docs, /metrics)
```

### Deploy a public demo

The dashboard runs standalone on its own route handlers (which serve the real measured
numbers), so the fastest public link needs no backend — deploy `frontend/` to Vercel.
Full instructions, including the containerised cloud path, are in **[DEPLOY.md](DEPLOY.md)**.

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

Building QuantML meant working through a set of problems across the full stack:

**Quantitative finance / ML:**
- Implementing walk-forward validation correctly in a time-series context — k-fold cross-validation causes lookahead bias and inflates performance metrics by 0.1–0.2 Sharpe
- Cross-sectional normalisation as a leakage-prevention technique
- Reporting both the frictionless signal Sharpe (1.19) and the net-of-cost backtest Sharpe (0.88), and treating the gap as the result rather than hiding it
- Multiple-testing correction via the Deflated Sharpe Ratio, backed by an append-only trial registry — the standard defence against backtest overfitting
- Per-row SHAP attribution without adding a dependency, using XGBoost's native `pred_contribs`

**Backend architecture:**
- A layered execution design where live trading is impossible by accident
- Graceful degradation across both the backend (falls back to mock if artifacts don't exist) and frontend (falls back to mock if backend is offline)
- Pydantic v2 response models that mirror TypeScript interfaces exactly — the same JSON shapes work against Next.js route handlers or FastAPI with no component changes
- Real-time WebSocket signal ticks in an async FastAPI app
- A 137-test suite plus CI that runs entirely offline by design — tests build their own seeded fixtures and exercise the same mock fallback the services use on a cold checkout, so the safety gates (live-trading lock, risk caps) are regression-tested on every push

**Frontend engineering:**
- Running a WebGL fragment shader simultaneously with CSS/Framer Motion particle systems in the same canvas layer without z-fighting
- SSR-safe Recharts with hydration-stable deterministic mock data
- A typed API client that transparently switches between the FastAPI backend and Next.js mock routes based on a single env var

---

<div align="center">

**Research platform. Signals are probabilistic model outputs — not financial advice.**

</div>
