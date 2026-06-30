"""
Snapshot the live API responses to JSON the frontend serves on a static deploy.

The FastAPI backend already maps the data/ artifacts into the exact shapes the
dashboard expects (mirrored contracts), so it's the single source of truth. This
boots the app in-process, calls each endpoint against the real artifacts, and writes
frontend/lib/snapshot/<name>.json. The Next.js route handlers serve those files, so
the standalone (no-backend) Vercel deploy shows real pipeline output, not mock data.

Re-run after a pipeline run to refresh the snapshot:

    python -m scripts.snapshot_api
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "backend", ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

OUT = ROOT / "frontend" / "lib" / "snapshot"

GET_ENDPOINTS = {
    "signals": "/api/signals",
    "metrics": "/api/metrics",
    "equity": "/api/equity",
    "trades": "/api/trades",
    "risk": "/api/risk",
    "models": "/api/models",
    "validation": "/api/validation",
    "monitoring": "/api/monitoring",
    "replay": "/api/replay",
}


def _write(name: str, payload) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    size = len(payload) if isinstance(payload, list) else len(payload or {})
    print(f"  {name:<12} {len(GET_ENDPOINTS) and ''}({size} items)")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    client = TestClient(app)

    for name, path in GET_ENDPOINTS.items():
        r = client.get(path)
        r.raise_for_status()
        _write(name, r.json())

    # the backtest is a POST with the default config
    r = client.post("/api/backtests", json={})
    r.raise_for_status()
    _write("backtests", r.json())

    print(f"Snapshot written to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
