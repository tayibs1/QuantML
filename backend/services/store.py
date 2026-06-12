"""
Read layer. Serve the real ML artifacts out of data/ when they're there, and
fall back to the seeded mock when they aren't, so the API (and the frontend)
work even before the pipeline has ever run.

Each getter returns (data, source) where source is "live" or "mock".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import mock_data as mock
from config import settings


def _load_json(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return None


def get_signals(signal_type: Optional[str] = None) -> tuple[list[dict], str]:
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
        real_names = {m.get("name") for m in real}
        # keep the mock baselines so the registry looks fuller; real champion goes first
        baselines = [m for m in mock.MODELS if m.get("name") not in real_names]
        fi = _normalise_fi(card.get("featureImportance") or mock.FEATURE_IMPORTANCE)
        return {"models": real + baselines, "featureImportance": fi}, "live"
    return {"models": mock.MODELS, "featureImportance": mock.FEATURE_IMPORTANCE}, "mock"


def signals_meta() -> dict:
    payload = _load_json(settings.signals_dir / "latest.json")
    if payload:
        return {"generatedAt": payload.get("generatedAt"), "count": payload.get("count")}
    return {"generatedAt": None, "count": len(mock.SIGNALS)}


def latest_prices() -> dict[str, float]:
    """ticker -> price, pulled from the live signals (execution preview uses it)."""
    data, _ = get_signals()
    return {s["ticker"]: s["price"] for s in data if s.get("price")}
