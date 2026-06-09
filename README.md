# QuantML

A full-stack **ML trading-research platform**: a Next.js terminal frontend, a
FastAPI backend, and a Python ML pipeline that turns real market data into
calibrated, risk-aware, explainable trading signals.

> Research & educational platform. It does not provide financial advice, execute
> live trades, or guarantee outcomes. See the disclaimer in the app's `/docs`.

## Monorepo layout

```
QuantML/
├── frontend/     Next.js 15 + TS + Tailwind + Motion — the website/terminal
├── backend/      FastAPI — serves the API the frontend consumes (REST + WS)
├── ml/           ML pipeline: ingestion → features → training → inference
├── data/         generated data & model artifacts (git-ignored)
├── docs/         architecture + backend + ML methodology reference
├── scripts/      dev helpers (dev.ps1 / dev.sh start the whole stack)
├── package.json  root orchestrator (npm run dev/build → frontend)
├── docker-compose.yml
└── .env.example  copy to .env and fill in
```

## Quickstart

### 1. Frontend (works standalone with built-in mock data)

```bash
npm run install:frontend      # one-time: install web deps
npm run dev                   # → http://localhost:3000
```

The web app fetches over HTTP from the built-in Next.js mock routes, so it's
fully functional with no backend running.

### 2. Backend (FastAPI — same JSON shapes)

```bash
npm run setup:backend         # one-time: venv + pip install (Windows)
# or:  cd backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
npm run backend               # → http://localhost:8000/docs
```

Then create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

Restart `npm run dev` — the frontend now talks to FastAPI instead of the mock
routes, with **zero component changes**.

### Run both at once

```bash
./scripts/dev.ps1     # Windows
./scripts/dev.sh      # macOS / Linux
```

## From demo → real

The frontend is done. Making the data **real** is the `backend/` + `ml/` work:

1. **Ingestion** (`ml/ingestion`) — download real OHLCV + fundamentals.
2. **Features** (`ml/features`) — build the ~84-feature matrix, point-in-time.
3. **Training** (`ml/training`) — walk-forward train + calibrate, log to MLflow.
4. **Inference** (`ml/inference`) — score the universe → BUY/HOLD/AVOID + drivers.
5. **Backend** (`backend/`) — replace each mock handler with the real source.
6. **RAG** — index filings/news into the vector store; wire the LLM.
7. **Real-time** — stream prices/signals over `WS /ws/signals`.

Full detail — every endpoint's contract and the ML methodology — is in
**[`docs/BACKEND.md`](docs/BACKEND.md)**.

## Tech

**Frontend:** Next.js (App Router) · TypeScript · Tailwind · Motion · Recharts ·
Three.js/react-three-fiber · Radix.
**Backend / ML:** FastAPI · Pydantic · pandas · XGBoost/LightGBM · MLflow ·
sentence-transformers + a vector store · an LLM for RAG.
