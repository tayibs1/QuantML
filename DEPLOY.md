# Deploying QuantML

Three ways to run it, smallest to biggest. The dashboard works **standalone** — its
Next.js route handlers serve the real measured numbers — so the fastest public demo
needs no backend at all.

---

## 1. Public demo (recommended) — Vercel, no backend

The dashboard runs on its own same-origin mock routes, which carry the real research
numbers. This is the one-click recruiter link.

1. Push to GitHub (done).
2. On [vercel.com](https://vercel.com) → **New Project** → import this repo.
3. Set **Root Directory = `frontend`** (Vercel auto-detects Next.js; `frontend/vercel.json`
   handles the rest). No environment variables needed.
4. Deploy. You get a live URL in ~2 minutes.

Or from the CLI:

```bash
npm i -g vercel
cd frontend && vercel --prod
```

To point the deployed dashboard at a live backend instead of the mock routes, set
`NEXT_PUBLIC_API_URL` (and `NEXT_PUBLIC_WS_URL`) in the Vercel project to your API URL.

---

## 2. Full stack locally — one command

```bash
docker compose up --build
```

- Dashboard → http://localhost:3000
- API → http://localhost:8000 (docs at `/docs`, Prometheus at `/metrics`)

Run the pipeline on a daily cadence too (dry-run plan by default):

```bash
docker compose --profile scheduler up --build
```

---

## 3. Full stack in the cloud (backend + frontend)

The backend ships as a container (`backend/Dockerfile`, build context = repo root).

- **Backend** → any container host (Render, Railway, Fly.io). Build with
  `backend/Dockerfile`; it exposes port `8000`. No required env for the demo; the API
  serves the bundled JSON artifacts and falls back to seeded data otherwise.
- **Frontend** → Vercel as above, with `NEXT_PUBLIC_API_URL` pointed at the backend URL.

---

## Environment variables

| Variable | Where | Default | Purpose |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | frontend | _(unset → mock routes)_ | point the dashboard at a live API |
| `NEXT_PUBLIC_WS_URL` | frontend | _(unset)_ | live WebSocket signal ticks |
| `EXECUTION_MODE` | backend | `backtest` | `backtest` \| `paper` \| `live` |
| `BROKER_PROVIDER` | backend | `none` | `alpaca` for paper trading |
| `ALPACA_API_KEY` / `ALPACA_API_SECRET` | backend | — | paper-trading credentials |
| `LIVE_TRADING_ENABLED` | backend | `false` | hard gate; live adapter refuses to construct otherwise |

See `.env.example` for the full list.

---

## Notes

- The image bundles the small JSON artifacts (model card, signals, drift, registry) so
  the API serves real numbers. The heavy parquet (`data/raw`, `data/processed`) is
  excluded; mount `data/` at runtime if you need a cold backtest re-simulation.
- This is a **research platform**. `EXECUTION_MODE=live` stays gated by design.
