"""
Filesystem layout shared across the ML pipeline.

These resolve to the SAME `data/` folder the backend reads from (anchored at the
repo root), so the ML side writes artifacts and the API side reads them with no
import coupling between the two.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = DATA_DIR / "models"
SIGNALS_DIR = DATA_DIR / "signals"

OHLCV_PATH = RAW_DIR / "ohlcv.parquet"
BENCHMARK_PATH = RAW_DIR / "benchmark.parquet"
FEATURES_PATH = PROCESSED_DIR / "features.parquet"
MODEL_PATH = MODELS_DIR / "xgb_signal.json"
MODEL_META_PATH = MODELS_DIR / "xgb_signal.meta.json"
MODEL_CARD_PATH = MODELS_DIR / "model_card.json"
SIGNALS_PATH = SIGNALS_DIR / "latest.json"


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, MODELS_DIR, SIGNALS_DIR):
        d.mkdir(parents=True, exist_ok=True)
