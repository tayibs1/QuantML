# QuantML — Frontend

The Next.js terminal UI. Runs standalone against built-in mock route handlers, or
against the FastAPI backend when `NEXT_PUBLIC_API_URL` is set.

> Run from the **repo root** with `npm run dev` (it proxies here), or directly:
> `cd frontend && npm install && npm run dev` → http://localhost:3000

## Wire to the real backend

Create `frontend/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

With it unset, the app uses the mock handlers in `app/api/*` (same JSON shapes).

## Pages

| Route         | What it is                                                        |
| ------------- | ----------------------------------------------------------------- |
| `/`           | Landing — WebGL shader hero, problem/solution, architecture, CTA  |
| `/dashboard`  | Command centre — KPIs, equity/drawdown, signals, RAG, risk alerts |
| `/signals`    | BUY/HOLD/AVOID cards with confidence, drivers, expected return    |
| `/backtests`  | Config panel, equity/drawdown/heatmap, metrics, trade history     |
| `/research`   | RAG assistant — grounded answers + sources + risk context         |
| `/models`     | Model registry, comparison, feature importance, experiments       |
| `/risk`       | Exposure, volatility regime, risk budget, drift/degradation       |
| `/docs`       | Methodology + limitations & disclaimers                           |

## Structure

```
app/
  page.tsx                 landing
  (app)/                   shared sidebar + status-bar shell
    dashboard|signals|backtests|research|models|risk|docs/
  api/                     route handlers (mock backend over HTTP)
components/
  charts/                  recharts wrappers (equity, drawdown, sparkline, …)
  landing/                 hero, shader background, nav, footer
  *.tsx                    MetricCard, SignalCard, GlassPanel, ResearchAssistant…
lib/
  mock-data.ts             seeded mock data + TS types  (the data contract)
  api.ts                   typed fetch client (Next routes ↔ FastAPI)
```

The TypeScript types in `lib/mock-data.ts` and the Pydantic models in
`../backend/schemas.py` are mirrored — they are the data contract. See
`../docs/BACKEND.md`.

## Tech

Next.js (App Router) · TypeScript · Tailwind CSS · Motion · Recharts ·
Three.js / react-three-fiber (shader hero) · lucide-react · Radix primitives.
