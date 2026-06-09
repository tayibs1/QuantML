# QuantML Backend (FastAPI)

A runnable skeleton of the QuantML API. Every endpoint returns the exact JSON
shape the Next.js frontend expects, so you can develop the UI against this
backend and incrementally replace each mock handler with the real pipeline.

## Run

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- Interactive docs: http://localhost:8000/docs
- Health check:      http://localhost:8000/health

## Point the frontend at it

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Restart `npm run dev` (from the repo root). The frontend's `lib/api.ts` now calls
FastAPI instead of the built-in Next.js route handlers. Nothing else changes.

## Endpoints

| Method | Path             | Returns                                            | Replace mock with…                              |
| ------ | ---------------- | -------------------------------------------------- | ----------------------------------------------- |
| GET    | `/health`        | service + model status                             | real liveness + model registry lookup           |
| GET    | `/metrics`       | dashboard KPIs                                      | live portfolio + latest backtest snapshot       |
| GET    | `/equity`        | equity / benchmark / drawdown series               | strategy results store                          |
| GET    | `/signals`       | per-ticker BUY/HOLD/AVOID + confidence + drivers   | `model.predict_proba()` + calibrated thresholds |
| GET    | `/models`        | model registry + feature importance                | MLflow registry + SHAP report                   |
| GET    | `/trades`        | closed trade ledger                                 | backtest / paper-trading ledger                 |
| GET    | `/risk`          | exposures, budget, regime, flags, rules            | positions + drift monitoring                    |
| POST   | `/research`      | grounded RAG answer + sources                       | retriever + LLM over your corpus                |
| WS     | `/ws/signals`    | live price / signal ticks                           | market-data feed + streaming inference          |

See `../docs/BACKEND.md` for the full data flow and the ML methodology.
