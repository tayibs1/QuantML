# `ml/` — Machine-learning pipeline

This is where the **real strategy** lives. It produces everything the backend
serves: signals, backtests, model metrics, and the model artifacts the API loads
at inference time. Today it's a scaffold; we build it out stage by stage.

```
ml/
├── ingestion/    market-data download + point-in-time storage  → data/raw
├── features/     causal feature engineering (~84 features)     → data/processed
├── training/     walk-forward training, calibration, SHAP      → data/models, mlruns/
└── inference/    load a model, score the universe, emit signals (used by backend)
```

## Pipeline (matches `docs/BACKEND.md` §3)

1. **ingestion** — pull daily OHLCV + fundamentals for the universe, split/dividend
   adjusted, point-in-time aligned. Persist to `data/raw`.
2. **features** — compute momentum / relative-strength / volume / volatility /
   mean-reversion / options / fundamentals features, z-scored cross-sectionally.
   Persist to `data/processed`.
3. **training** — define the 5-day-forward target with a dead-band, train
   XGBoost/LightGBM with **expanding-window walk-forward** validation, calibrate
   probabilities, save SHAP global importance, log runs to MLflow, register the
   model under `data/models`.
4. **inference** — load the registered model, score the latest feature vector per
   name, map probabilities → BUY/HOLD/AVOID, attach per-row SHAP drivers. The
   FastAPI backend imports this to serve `GET /signals`.

## Run (once implemented)

```bash
python -m ml.ingestion.download --universe NASDAQ100 --start 2018-01-01
python -m ml.features.build
python -m ml.training.walk_forward --model xgboost
python -m ml.inference.score        # writes today's signals the API reads
```
