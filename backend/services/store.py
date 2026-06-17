"""
Read layer. Serve the real ML artifacts out of data/ when they're there, and
fall back to the seeded mock when they aren't, so the API (and the frontend)
work even before the pipeline has ever run.

Each getter returns (data, source) where source is "live" or "mock".
"""
from __future__ import annotations

import json
from pathlib import Path

import mock_data as mock
from config import settings


def _load_json(path: Path) -> dict | None:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return None


def get_signals(signal_type: str | None = None) -> tuple[list[dict], str]:
    payload = _load_json(settings.signals_dir / "latest.json")
    if payload and payload.get("signals"):
        data, source = payload["signals"], "live"
    else:
        data, source = mock.SIGNALS, "mock"
    if signal_type:
        data = [s for s in data if s["signal"] == signal_type.upper()]
    return data, source


def _normalise_model(m: dict) -> dict:
    """Coerce model_card fields to match the frontend ModelRecord contract."""
    m = dict(m)
    # accuracy is stored as a raw percent (37.3); the frontend wants a fraction (0.373)
    if m.get("accuracy", 0) > 1:
        m["accuracy"] = round(m["accuracy"] / 100, 4)
    # cagr stays as a raw percent (26.7) - the frontend already renders it with %
    return m


def _normalise_fi(fi: list[dict]) -> list[dict]:
    """Normalise feature importance scores to 0-1 fractions.

    Training writes raw gain values (they sum to ~100). FeatureImportanceChart
    wants fractions and formats them itself as (v * 100).toFixed(1)%.
    """
    if not fi:
        return fi
    if fi[0].get("importance", 0) > 1:
        total = sum(item["importance"] for item in fi) or 1.0
        return [{"feature": item["feature"], "importance": round(item["importance"] / total, 4)}
                for item in fi]
    return fi


def get_models() -> tuple[dict, str]:
    card = _load_json(settings.models_dir / "model_card.json")
    if card and card.get("models"):
        real = [_normalise_model(m) for m in card["models"]]
        fi = _normalise_fi(card.get("featureImportance") or mock.FEATURE_IMPORTANCE)
        # once the baseline comparison has run there are several real models, so
        # show only those. before that (champion only) pad with mock baselines so
        # the registry doesn't look bare - but never fake it once real ones exist.
        if len(real) < 3:
            names = {m.get("name") for m in real}
            real = real + [m for m in mock.MODELS if m.get("name") not in names]
        return {
            "models": real, "featureImportance": fi,
            "experiments": recent_trials(), "registry": model_registry(),
        }, "live"
    return {
        "models": mock.MODELS,
        "featureImportance": mock.FEATURE_IMPORTANCE,
        "experiments": recent_trials(),
        "registry": model_registry(),
    }, "mock"


def model_registry() -> dict:
    """Versioned-champion history from data/models/registry.json (DSR-gated promotions).

    Plain artifact read, like the trial log — keeps the backend off the ML imports.
    Returns an empty registry (not an error) before any model has been registered.
    """
    reg = _load_json(settings.models_dir / "registry.json")
    if not reg or not reg.get("versions"):
        return {"versions": [], "championId": None}
    return {"versions": reg["versions"], "championId": reg.get("championId")}


def recent_trials(limit: int = 8) -> list[dict]:
    """Format the most recent entries from the trial registry as experiment rows.

    The registry (data/research/trials.jsonl) is the real append-only log every
    backtest and tuning run writes to. Reading it straight off disk keeps the
    backend from importing the ML side - it's just an artifact like any other.
    Empty/absent file falls back to the seeded experiments so the panel isn't bare.
    """
    path = settings.data_dir / "research" / "trials.jsonl"
    try:
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except OSError:
        return list(mock.EXPERIMENTS)
    rows = []
    for ln in lines[-limit:]:
        try:
            t = json.loads(ln)
        except json.JSONDecodeError:
            continue
        metrics = t.get("metrics", {})
        sharpe = metrics.get("sharpe")
        rows.append({
            "id": t.get("trial_id", "")[:8] or "trial",
            "model": t.get("kind", "trial"),
            "metric": f"Sharpe {sharpe:.2f}" if isinstance(sharpe, int | float) else "-",
            "status": "finished",
            "time": (t.get("timestamp") or "")[:10],
            "tags": t.get("tags", []),
        })
    rows.reverse()  # newest first
    return rows or list(mock.EXPERIMENTS)


def signals_meta() -> dict:
    payload = _load_json(settings.signals_dir / "latest.json")
    if payload:
        return {"generatedAt": payload.get("generatedAt"), "count": payload.get("count")}
    return {"generatedAt": None, "count": len(mock.SIGNALS)}


def latest_prices() -> dict[str, float]:
    """ticker -> price, pulled from the live signals (execution preview uses it)."""
    data, _ = get_signals()
    return {s["ticker"]: s["price"] for s in data if s.get("price")}
