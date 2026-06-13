<div align="center">

# QuantML — Roadmap

**From a validated research signal to gated, real-money execution — without ever letting the model trade by accident.**

</div>

This roadmap is deliberately honest about what is *done*, what is *in progress*, and
what is *gated behind hard criteria*. The whole point of the architecture is that
moving between phases is **additive** — each layer plugs into the same contracts, so
"turning on paper trading" or, much later, "turning on live" is a configuration and
risk decision, never a rewrite.

```
Phase 0 ─────────► Phase 1 ─────────► Phase 2 ─────────► Phase 3
Research            Production          Paper trading       Live trading
(validated)         hardening           (forward test)      (hard-gated)
   ✅                 🔄                    ⏭️                   🔒
```

| Legend | Meaning |
|---|---|
| ✅ | Shipped and tested |
| 🔄 | In progress |
| ⏭️ | Designed, next up |
| 🔒 | Gated — blocked behind explicit criteria, off by design |

---

## Maturity snapshot

| Capability | State | Notes |
|---|---|---|
| Data ingestion (117k bars, split/div adj.) | ✅ | Direct Yahoo HTTP, no SDK |
| Causal feature engineering (24 features, x-sec z) | ✅ | Leakage-tested |
| Walk-forward training + Optuna tuning | ✅ | Champion DSR-validated |
| Anti-overfit trial registry (PSR / DSR) | ✅ | Append-only, multiple-testing aware |
| Net-of-cost backtest engine | ✅ | Risk caps + transaction costs |
| Risk engine (name/sector/gross caps) | ✅ | Long-only, confidence-sized |
| Execution: **backtest** adapter | ✅ | Simulated fills |
| Execution: **paper** adapter (Alpaca) | ✅ | Implemented, env-gated, offline-tested |
| Execution: **live** adapter | 🔒 | Refuses to construct unless explicitly enabled |
| FastAPI backend + Next.js dashboard | ✅ | Graceful mock fallback both sides |
| CI (ruff + pytest + next build) | ✅ | Runs fully offline |
| Data-quality gates (schema/rows/freshness) | ✅ | Blocks promotion on critical failure |
| Feature-drift monitoring (PSI) | ✅ | OK/WARN/ALERT, served at `/api/monitoring` |
| Pipeline orchestrator + scheduled CI | ✅ | Staged graph with the gate inline |
| Model registry / versioning | ⏭️ | Phase 1 |
| Live-vs-backtest tracking + P&L reconciliation | ⏭️ | Phase 2 (needs paper feed) |
| Live risk controls + kill switch | 🔒 | Phase 3 |

---

## Phase 0 — Research foundation ✅ *(shipped)*

The credibility base. Everything downstream inherits its honesty from here.

- Walk-forward (never k-fold) validation; cross-sectional z-scoring to prevent leakage.
- Champion = Optuna-tuned XGBoost, **signal Sharpe 1.19 / net-of-cost 0.88**, every
  number out-of-sample only.
- Baselines (RF, logistic, momentum), regime breakdown, and feature ablation run on
  identical folds — and reported even where they're unflattering.
- Deflated Sharpe Ratio over an append-only trial registry: the standard defence
  against backtest overfitting.

---

## Phase 1 — Production hardening 🔄 *(in progress)*

Turn the research repo into a system that runs itself reliably.

- [x] **Data quality gates** — `ml/validation.py` runs schema / row-count / finite-value /
      staleness checks and `gate()` blocks promotion on any *critical* failure (never
      train or score on bad data). The report is served at `/api/monitoring`.
- [x] **Feature-drift monitoring** — `ml/research/drift.py` computes per-feature **PSI**
      (latest cross-section vs the historical reference window), grading each OK / WARN /
      ALERT, written to `drift.json` and surfaced at `/api/monitoring`.
- [x] **Pipeline orchestrator + schedule** — `ml/pipeline.py` runs the staged graph
      (`ingest → features → validate → train → score → drift`) with the data-quality gate
      wired *between* feature-build and training, structured logging, and stage selection;
      `.github/workflows/pipeline.yml` runs the daily score/drift cadence (a real run is
      gated on the data feed + Alpaca secrets).
- [ ] **Model registry + versioning** — promote/rollback champions (MLflow, or extend the
      existing trial registry) with the Deflated Sharpe Ratio as the promotion gate.
- [ ] **Full observability** — request tracing and a Prometheus `/metrics` endpoint
      (structured pipeline logging is already in; this extends it).
- [ ] **Live-vs-backtest tracking** — tracking error / calibration decay against the paper
      account (lands with Phase 2, once there's a live feed to compare to).
- [ ] **Containerised one-command deploy** — extend `docker-compose` to a cloud deploy
      (backend + frontend + scheduler).

---

## Phase 2 — Paper trading ⏭️ *(next)*

Forward-test the strategy on a live data feed with **fake money** — the only honest way
to find out whether the backtest survives contact with reality.

- [x] **Paper execution adapter** — `PaperExecutionAdapter` submits notional market
      orders to the Alpaca paper API; env-gated (`EXECUTION_MODE=paper`,
      `BROKER_PROVIDER=alpaca`, `ALPACA_API_KEY/SECRET`), offline-tested.
- [ ] **Account reconciliation** — pull Alpaca positions/equity, diff against the risk
      engine's intended book, surface drift in the dashboard.
- [ ] **Scheduled rebalance** — run signals → risk → paper submit on the real cadence
      (weekly), with idempotency and a dry-run mode.
- [ ] **Live P&L + track record** — accumulate the paper equity curve next to the
      backtest's, compute realised Sharpe/drawdown, and feed it back into the trial
      registry as out-of-sample evidence.
- [ ] **Slippage & fill model validation** — compare real paper fills to the 13bps
      cost assumption; recalibrate the backtest if reality disagrees.

**Exit criteria → Phase 3:** ≥ 3 months of paper trading, live-vs-backtest tracking
error within tolerance, realised paper Sharpe consistent with OOS expectations, and no
unexplained risk-limit breaches.

---

## Phase 3 — Live trading 🔒 *(gated — off by design)*

Real money. This phase stays **impossible by accident**: `LiveExecutionAdapter` refuses
to even construct unless `LIVE_TRADING_ENABLED=true`, and `submit()` is intentionally
unimplemented until the controls below exist.

- [ ] **Hard risk controls** — pre-trade checks (max position, max gross, per-order
      notional cap), daily loss limit, and an automatic **kill switch**.
- [ ] **Order lifecycle management** — partial fills, retries, cancel/replace,
      idempotent submission, and full audit logging of every order.
- [ ] **Reconciliation & alerting** — continuous position/cash reconciliation with the
      broker; page a human on any divergence.
- [ ] **Compliance & sign-off** — documented risk review, capital allocation policy,
      and explicit human authorisation per the architecture's intent.
- [ ] **Start tiny** — minimal capital, single-name caps, scale only as the live track
      record earns it.

---

## What makes this a standout project

- **Honest quant methodology end-to-end** — walk-forward only, both frictionless and
  net-of-cost numbers reported, DSR multiple-testing correction, and weaknesses
  disclosed (loses money in 2022; only the champion was tuned). This is what separates
  a real research platform from a curve-fit demo.
- **Safety by construction** — the model *cannot* execute a trade. Signals flow through
  an independent risk engine into a swappable execution adapter, and live trading is a
  hard-gated, unimplemented path. Recruiters in trading/fintech read this immediately.
- **Full-stack, production-shaped** — typed FastAPI ↔ Next.js with mirrored contracts,
  graceful degradation on both sides, real-time WebSocket signals, and CI that runs
  entirely offline.
- **Interpretability** — per-signal SHAP attributions, not a black box.

## What's left for the "10/10 portfolio piece" checklist

- [ ] One-command cloud deploy + a public live demo URL.
- [ ] A short Loom/GIF walkthrough embedded in the README.
- [ ] The Phase 1 scheduler + monitoring (shows it runs unattended).
- [ ] A live paper-trading equity curve on the dashboard (forward, not backtest).
- [ ] An architecture decision record (ADR) or short write-up of the key trade-offs.

---

<div align="center">

**Research platform. Signals are probabilistic model outputs — not financial advice.**

</div>
