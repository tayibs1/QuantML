# QuantML — System, Backend & ML Reference

This document explains **what every page does**, **exactly what the backend must
implement** for each page to show real, live data, and **how the machine
learning actually produces signals**. It is the bridge between the frontend you
can see today (mock data over a real HTTP layer) and a production pipeline.

---

## 1. Architecture at a glance

```
                       ┌─────────────────────────────────────────────┐
                       │                  FRONTEND                    │
                       │  Next.js App Router · React · Tailwind       │
                       │  Components ──> lib/api.ts (fetch)           │
                       └───────────────┬─────────────────────────────┘
                                       │ HTTP / WS  (JSON)
            NEXT_PUBLIC_API_URL unset  │  set → http://localhost:8000
              ┌────────────────────────┴───────────────────────┐
              ▼                                                 ▼
   ┌────────────────────────┐                     ┌────────────────────────────┐
   │ Next.js route handlers │   (drop-in mock)    │  Python FastAPI backend     │
   │ app/api/*              │ ───── same shape ── │  backend/main.py            │
   └────────────────────────┘                     └──────────────┬──────────────┘
                                                                  │
   ┌──────────────────────────────────────────────────────────────────────────┐
   │                         PRODUCTION DATA PLANE (to build)                    │
   │                                                                            │
   │  Market data ─▶ Feature store ─▶ ML model ─▶ Backtest engine ─▶ Risk layer │
   │  (OHLCV)        (84 features)    (predict_proba)  (walk-forward)  (sizing)  │
   │                                       │                                     │
   │                                       ▼                                     │
   │                         Vector store + LLM  (RAG research)                  │
   └──────────────────────────────────────────────────────────────────────────┘
```

**Key idea:** the frontend never imports business logic. It calls `lib/api.ts`,
which calls HTTP endpoints. Today those endpoints are Next.js route handlers
returning seeded mock data; flip `NEXT_PUBLIC_API_URL` to use the FastAPI backend
with byte-identical shapes. You replace mock internals one endpoint at a time
without touching a single component.

The data contracts live in two mirrored places:
- TypeScript: `lib/mock-data.ts` (the source of truth for shapes)
- Python: `backend/schemas.py` (Pydantic models matching them 1:1)

---

## 2. Page-by-page: what it does + what the backend must provide

### `/` — Landing
**Shows:** marketing hero (WebGL shader background), the problem/solution story,
an animated architecture diagram, and a *live preview* of the dashboard.
**Data:** none required — it reuses sample series for the preview. No backend work.

---

### `/dashboard` — Command centre
**Shows:** 8 KPI cards (portfolio value, strategy & benchmark return, Sharpe, max
drawdown, win rate, model confidence, exposure), the equity curve vs QQQ, a
drawdown curve, the latest-signals table, the RAG assistant, and risk alerts.

**Endpoints it needs:**
- `GET /metrics` → the 8 KPI values + deltas. *Backend:* compute from the live
  portfolio NAV and the latest backtest snapshot (returns, Sharpe = mean/std·√252,
  drawdown from the running peak, win rate from the trade ledger).
- `GET /equity?range=N` → `[{date, strategy, benchmark, drawdown}]`. *Backend:*
  the strategy equity curve and the benchmark (QQQ) rebased to 100, plus the
  underwater (drawdown) series.
- `GET /signals` → latest signals (see `/signals` page).
- `GET /risk` → the `flags[]` array drives the alert panel.
- `POST /research` → powers the embedded assistant.

**Real-time:** subscribe to `WS /ws/signals` to live-update the ticker tape and
confidence rings; poll `/metrics` every 30–60s, or push NAV updates over the same
socket.

---

### `/signals` — Model predictions
**Shows:** filterable cards (BUY / HOLD / AVOID) per ticker with a confidence
ring, expected 5-day return, risk level, the **top feature drivers**, model
version, and an "Explain with Research AI" deep-link.

**Endpoint:** `GET /signals?type=BUY|HOLD|AVOID`
Returns per ticker:
```ts
{ ticker, company, signal, confidence,        // 0–100, = max class probability
  expectedReturn5d, risk, model,              // model version that scored it
  drivers: string[],                          // top SHAP features for THIS row
  price, change, sector }
```
**Backend must implement:** for each name in the universe, take the most recent
feature vector, run `model.predict_proba()`, map probabilities to BUY/HOLD/AVOID
via the calibrated thresholds, attach the per-row SHAP top-k as `drivers`, and the
expected forward return from the regression head (or the probability-weighted
expectation). See §3 for how those numbers are produced.

---

### `/backtests` — Strategy evaluation
**Shows:** a configuration panel (universe, model, period, rebalance, cost &
slippage sliders), tabbed equity / drawdown / **monthly-returns heatmap**, a
metrics strip (CAGR, Sharpe, Sortino, max DD, vol, turnover, win rate, profit
factor), and a trade-history table.

**Endpoints:**
- `GET /equity` → curves (above).
- `GET /trades` → closed trades `[{id,date,ticker,side,entry,exit,pnl,ret,hold}]`.
- *(add)* `POST /backtests` with the config body to **run** a backtest and return
  the metrics + curves + trades + monthly grid. The config panel is already the
  request shape: `{ universe, model, period, rebalance, costBps, slippageBps }`.

**Backend must implement:** the walk-forward backtest engine (§3.4) that applies
costs/slippage on every fill, tracks turnover, and emits the metrics, curves,
trade ledger, and the year×month return grid.

---

### `/research` — RAG market intelligence
**Shows:** a chat assistant. Each answer renders: the **answer**, **retrieved
sources** (filings/news/earnings/model reports with type + date + snippet),
**model signal context** (ticker · signal · confidence), **risk warnings**, and an
**interpretation-confidence** bar. Deep-links from signal cards via `?ticker=`.

**Endpoint:** `POST /research { prompt }` → `RagResponse` (see schema).
**Backend must implement:** retrieval-augmented generation — §4.

---

### `/models` — Registry & experiments
**Shows:** registry cards (XGBoost-v3 *production candidate*, LightGBM-v2 champion,
Random Forest, Logistic Regression, LSTM experimental, Momentum baseline) with
Sharpe / CAGR / max-DD / drift / AUC / features; a comparison table; a feature-
importance bar chart; and an MLflow-style experiment list.

**Endpoint:** `GET /models` → `{ models[], featureImportance[] }`.
**Backend must implement:** read from your **model registry** (MLflow works
directly — model name, version, stage, metrics, params) and the **SHAP global
importance** report saved at train time. The "running/finished" experiment feed
maps to MLflow runs.

---

### `/risk` — Risk controls
**Shows:** an auto-applied risk banner, exposure-by-asset and exposure-by-sector
donuts, a volatility-regime chart (implied vs realized), a risk-budget panel
(gross, single-name, sector, VaR, beta vs limits), the position-sizing rules, and
the drift/degradation alerts.

**Endpoint:** `GET /risk` → `{ flags, budget, exposureByAsset, exposureBySector,
volatilityRegime, positionRules }`.
**Backend must implement:** aggregate **current positions** into exposures;
compute **VaR** and **beta**; compute the **volatility regime** (realized vol
percentile, e.g. EWMA or GARCH); run **drift monitoring** (PSI/KS per feature) and
**degradation** checks (rolling live-vs-backtest Sharpe) to generate `flags`.

---

### `/docs` — Methodology
**Shows:** the written methodology + disclaimers. Static; no backend.

---

## 3. How the machine learning predicts (the strategy)

QuantML is a **supervised, cross-sectional, short-horizon classification**
strategy with a risk overlay. It is *not* a black box that "predicts price" — it
ranks names by the probability of a favorable 5-day move and sizes positions under
explicit risk limits.

### 3.1 Data ingestion
Daily **OHLCV** + fundamentals for the universe (default NASDAQ-100), **point-in-
time** aligned: only information available at the close of day *t* may be used to
predict *t+1…t+5*. Prices are split/dividend adjusted; constituent history is
survivorship-bias-free where available. *(Endpoint owner: market-data store.)*

### 3.2 Feature engineering (~84 features per name, per day)
Computed **causally** (no future bars) and standardized **cross-sectionally**
within each rebalance (z-scored across the universe so the model learns relative,
not absolute, signals):
- **Momentum**: returns over 5/20/60/120 days.
- **Relative strength**: name return minus sector/universe return (percentile).
- **Volume**: z-scored volume, dollar-volume, on-balance-volume slope.
- **Volatility regime**: realized vol, vol-of-vol, ATR, regime percentile.
- **Mean reversion**: distance from moving averages, RSI, Bollinger position.
- **Options-derived**: implied vol level, 25-delta put/call skew.
- **Fundamental/revisions**: earnings-estimate revisions, surprise, valuation z.
- **Macro**: rates level/changes, sector breadth, market regime flags.

### 3.3 Target definition (what the model learns)
The label is the **5-day forward return**, discretized with a neutral dead-band so
the model isn't trained on noise:
```
fwd_ret = close[t+5]/close[t] − 1
BUY    if fwd_ret >  +θ      (e.g. +1.0%)
AVOID  if fwd_ret <  −θ
HOLD   otherwise (inside the band)
```
`θ` (and the probability thresholds in 3.5) are calibrated **on the training fold
only**, then frozen for the out-of-sample test — this is what prevents the
look-ahead bias that kills most notebook strategies.

### 3.4 Training & **walk-forward** validation
Models are tree ensembles (XGBoost / LightGBM are the workhorses; Random Forest &
Logistic Regression are baselines; an LSTM is experimental). Validation is
**expanding-window walk-forward**, not a random split:
```
Fold k:  train on [start … tₖ]   →   test on (tₖ … tₖ₊₁]   (strictly future)
repeat for 12 folds, retraining each step — exactly how you'd redeploy live.
```
Reported metrics (`/models`) are the **out-of-sample** aggregates: AUC, accuracy,
and the *strategy* metrics that actually matter — Sharpe, CAGR, max drawdown.

### 3.5 From probabilities to a signal
`model.predict_proba(x)` returns class probabilities. The **confidence** shown in
the UI is the winning class probability ×100. Probabilities are **calibrated**
(Platt/isotonic) so "78%" means roughly a 78% empirical hit rate. Mapping:
```
p = predict_proba(features_today)         # {BUY, HOLD, AVOID}
signal     = argmax(p)
confidence = round(100 · max(p))
drivers    = top-k SHAP features for this row   → the "Top drivers" chips
expReturn5d= regression head OR Σ p·class_mean_return
```
This is the payload of `GET /signals`. Each row is one `model.predict_proba` call
plus a SHAP attribution.

### 3.6 Backtest engine (turning signals into a track record)
For each rebalance: take the model's signals, form a long (and optionally short)
book, **apply transaction costs + slippage on every fill** (the sliders on
`/backtests`), track **turnover**, and mark the book daily. Output: the equity
curve, the underwater/drawdown curve, the monthly-return grid, the trade ledger,
and the headline metrics — *net of costs*, because a strategy that only works gross
of costs isn't a strategy.

### 3.7 Risk layer (between "signal" and "position")
A signal is **not** a position until the risk layer approves it:
- **Volatility-scaled, Kelly-capped sizing** (capped at 0.5× Kelly).
- **Hard caps**: 20% per name, 40% per sector, gross ≤ 100%.
- **Drawdown stops**: soft de-risk at −15%, full de-risk at −20%.
- **Regime gate**: no new entries when realized vol > 90th percentile; in elevated
  regimes sizing is automatically cut (the "−35%" banner on `/risk`).
This layer produces the exposures and `flags` served by `GET /risk`.

### 3.8 Monitoring (is the model still trustworthy?)
Production models drift. QuantML tracks **feature drift** (PSI/KS per feature),
**signal decay** (rolling hit-rate), and **live-vs-backtest Sharpe**. Threshold
breaches become the warnings on `/risk` and `/dashboard`, and trigger the
scheduled walk-forward **retrain**.

---

## 4. The RAG research assistant (`POST /research`)

The assistant **explains** signals; it never trades. Pipeline to implement:
1. **Embed** the user prompt (e.g. `sentence-transformers`).
2. **Retrieve** top-k chunks from a **vector store** (Chroma / pgvector / Pinecone)
   indexed over: SEC filings, market news, earnings transcripts, and internal
   **model reports** (SHAP attributions, drift logs, backtest summaries).
3. **Assemble context**: retrieved chunks **+** the live signal for the ticker
   (from `/signals`) **+** the current risk snapshot (from `/risk`).
4. **Generate** with an LLM, instructed to cite sources and never advise.
5. **Return** the structured `RagResponse`:
```ts
{ prompt, answer,
  sources: [{ title, type, date, snippet }],   // what was retrieved
  signalContext: { ticker, signal, confidence, model },
  riskWarnings: string[],                       // pulled from the risk layer
  confidence }                                  // interpretation confidence
```
The UI renders each section verbatim, so as long as you honor this shape the
existing `/research` and dashboard panels light up with real answers.

---

## 5. Real-time data

Two complementary mechanisms:
- **WebSocket** `WS /ws/signals` (already stubbed in `backend/main.py`) streams
  price/confidence ticks ~1.5s. Wire the ticker tape and confidence rings to it.
  Frontend sketch:
  ```ts
  const ws = new WebSocket(`${WS_BASE}/ws/signals`);
  ws.onmessage = (e) => setTicks(JSON.parse(e.data).data);
  ```
- **Polling / SSE** for slower aggregates: revalidate `/metrics`, `/equity`,
  `/risk` every 30–60s (Next.js `revalidate`, SWR, or React Query).

For a fully live build, add a streaming-inference service that re-scores signals
on each bar and publishes onto the same socket.

---

## 6. Go-live checklist

1. Stand up `backend/` (`uvicorn main:app`) and set `NEXT_PUBLIC_API_URL`.
2. Replace each handler's mock with the real source (the `TODO`s in `main.py`):
   market-data store → feature store → `model.predict_proba` → backtest results →
   risk aggregation → vector store + LLM.
3. Move secrets to env vars; lock CORS to your real origin.
4. Add auth (the frontend "Sign in" is a placeholder) — JWT/session at the API.
5. Add the streaming-inference worker + persist runs to MLflow.
6. Keep `lib/mock-data.ts` and `backend/schemas.py` in sync — they are the contract.
```
```
