"""
Shared pytest setup.

Two things every test relies on:

  1. Import paths. The ml/ package imports as `ml.*` from the repo root, while the
     backend modules (config, portfolio, backtesting, ...) are top-level when
     backend/ is on the path - that's how uvicorn runs them. We put both on
     sys.path here so tests can `import ml.labels...` and `import portfolio`
     side by side, exactly like the running services do.

  2. Synthetic data. Most units (features, labels, metrics) need a frame of
     prices or features but must not touch the network or the real data/ artifacts
     (those are gitignored and absent in CI). The fixtures below build small,
     seeded, deterministic frames so every test is reproducible and offline.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (ROOT, ROOT / "backend"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))


def _make_ohlcv(n_tickers: int = 12, n_days: int = 320, seed: int = 7) -> pd.DataFrame:
    """A seeded geometric-random-walk OHLCV panel, long format.

    n_days defaults past the 252-bar warmup the longest feature (52w / sma200)
    needs, so compute_features has usable rows to return.
    """
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2022-01-03", periods=n_days)
    frames = []
    for k in range(n_tickers):
        rets = rng.normal(0.0004, 0.018, n_days)
        close = 100.0 * np.exp(np.cumsum(rets))
        openp = close * (1 + rng.normal(0, 0.004, n_days))
        high = np.maximum(openp, close) * (1 + rng.uniform(0, 0.008, n_days))
        low = np.minimum(openp, close) * (1 - rng.uniform(0, 0.008, n_days))
        vol = rng.uniform(1e6, 5e6, n_days)
        frames.append(pd.DataFrame({
            "date": dates,
            "ticker": f"TK{k:02d}",
            "open": openp,
            "high": high,
            "low": low,
            "close": close,
            "volume": vol,
        }))
    return pd.concat(frames, ignore_index=True)


@pytest.fixture(scope="session")
def make_ohlcv():
    """Factory so a test can build its own panel with a different shape."""
    return _make_ohlcv


@pytest.fixture(scope="session")
def synthetic_ohlcv() -> pd.DataFrame:
    return _make_ohlcv()


@pytest.fixture(scope="session")
def synthetic_features(synthetic_ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Run the real feature pipeline over the synthetic panel."""
    from ml.features.build import compute_features

    return compute_features(synthetic_ohlcv)


@pytest.fixture
def label_frame() -> pd.DataFrame:
    """A tiny [date, ticker, fwd_ret_5] frame with enough dates per name that
    the 5-bar event end (t1) is non-null for the early rows."""
    rng = np.random.default_rng(3)
    dates = pd.bdate_range("2024-01-01", periods=12)
    tickers = [f"TK{i}" for i in range(6)]
    rows = []
    for d in dates:
        for t in tickers:
            rows.append({"date": d, "ticker": t, "fwd_ret_5": float(rng.normal(0, 0.03))})
    return pd.DataFrame(rows)
