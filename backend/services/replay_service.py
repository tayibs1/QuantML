"""
Signal-replay scenarios for the dashboard's interactive demo.

Each scenario is the production model's call on a real historical setup: the signal
(BUY / HOLD / AVOID), the conviction and the SHAP drivers behind it, and the price
path that followed, benchmarked against QQQ. The model, prices and benchmark are all
read from the artifacts, so the calls and outcomes are real.

This is a *teaching* view of how the model reasons, driven by the shipped model on
past setups. The rigorous walk-forward, out-of-sample numbers live on the Backtests
and Validation pages; the picks here are curated for variety (all three classes,
different sectors and dates) and deliberately include a couple of honest misses.
"""
from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from config import settings

HORIZON = 20      # trading days held / evaluated after the signal
LOOKBACK = 25     # trading days of context drawn before the signal
NOTIONAL = 10_000  # illustrative position size for the P&L reveal

# Curated setups (ticker, signal date). The model supplies the call, conviction and
# drivers; the forward price path supplies the outcome. Mixed classes and sectors,
# with two honest misses (NFLX lagged after a BUY; INTC crashed after a HOLD).
_PICKS: list[tuple[str, str]] = [
    ("MU", "2026-04-06"),
    ("INTC", "2025-03-05"),
    ("NFLX", "2026-03-25"),
    ("TSLA", "2025-01-28"),
    ("MDLZ", "2025-04-21"),
    ("VRTX", "2025-04-08"),
    ("PEP", "2025-05-14"),
    ("IDXX", "2025-09-04"),
    ("INTC", "2024-07-08"),
]


def _add_root_to_path() -> None:
    root = str(Path(__file__).resolve().parents[2])
    if root not in sys.path:
        sys.path.insert(0, root)


@lru_cache(maxsize=1)
def _ohlcv() -> pd.DataFrame:
    df = pd.read_parquet(settings.data_dir / "raw" / "ohlcv.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"])


@lru_cache(maxsize=1)
def _bench() -> pd.DataFrame:
    df = pd.read_parquet(settings.data_dir / "raw" / "benchmark.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


@lru_cache(maxsize=1)
def _features() -> pd.DataFrame:
    df = pd.read_parquet(settings.data_dir / "processed" / "features.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df


@lru_cache(maxsize=1)
def _model_bits():
    """(model, class->signal map, FEATURE_COLS, drivers fn) or None if unavailable."""
    _add_root_to_path()
    from ml.features.build import FEATURE_COLS
    from ml.inference.score import _drivers

    model = joblib.load(settings.data_dir / "models" / "xgb_signal.joblib")
    meta = json.loads((settings.data_dir / "models" / "xgb_signal.meta.json").read_text())
    class_to_signal = {int(k): v for k, v in meta["class_to_signal"].items()}
    return model, class_to_signal, list(FEATURE_COLS), _drivers


def _vol_regime(ticker: str, date: pd.Timestamp) -> str | None:
    s = _ohlcv()
    px = s[(s["ticker"] == ticker) & (s["date"] <= date)]["close"]
    if len(px) < 21:
        return None
    vol_z = px.pct_change().rolling(20).std().iloc[-1] * np.sqrt(252)
    if not np.isfinite(vol_z):
        return None
    # crude bucket against typical annualised vol
    if vol_z < 0.25:
        return "Low"
    if vol_z < 0.4:
        return "Moderate"
    if vol_z < 0.6:
        return "High"
    return "Elevated"


def _call(ticker: str, date: pd.Timestamp):
    """(signalType, conviction%, drivers[3]) from the production model, or None."""
    try:
        model, class_to_signal, feature_cols, drivers_fn = _model_bits()
    except Exception:
        return None
    feats = _features()
    row = feats[(feats["ticker"] == ticker) & (feats["date"] <= date)].sort_values("date").tail(1)
    if row.empty:
        return None
    X = row[feature_cols]
    proba = model.predict_proba(X)[0]
    cls = int(proba.argmax())
    drivers = drivers_fn(model, X, np.array([cls]))[0]
    return class_to_signal[cls], round(float(proba[cls]) * 100, 1), list(drivers)


def _company(ticker: str) -> tuple[str, str]:
    try:
        _add_root_to_path()
        from ml.universe import company, sector
        return company(ticker), sector(ticker)
    except Exception:
        return ticker, "—"


def _verdict(signal: str, ret: float, bench_ret: float | None) -> tuple[bool, str]:
    """Was the call right? BUY/AVOID judged against QQQ; HOLD against staying flat."""
    b = bench_ret if bench_ret is not None else 0.0
    if signal == "BUY":
        ok = ret > b
        return ok, ("beat QQQ" if ok else "lagged QQQ")
    if signal == "AVOID":
        ok = ret < b
        return ok, ("underperformed" if ok else "outran QQQ")
    ok = abs(ret) <= 5  # HOLD: right if it stayed roughly flat
    return ok, ("stayed flat" if ok else "moved sharply")


def _scenario(ticker: str, date_str: str) -> dict | None:
    call = _call(ticker, pd.Timestamp(date_str))
    if call is None:
        return None
    signal, conviction, drivers = call

    s = _ohlcv()
    px = s[s["ticker"] == ticker][["date", "close"]].reset_index(drop=True)
    entry_date = pd.Timestamp(date_str)
    entry_i = int((px["date"] - entry_date).abs().idxmin())
    exit_i = entry_i + HORIZON
    if exit_i >= len(px):
        return None
    lo = max(0, entry_i - LOOKBACK)
    window = px.iloc[lo : exit_i + 1].copy()

    entry_close = float(px["close"].iloc[entry_i])
    exit_close = float(px["close"].iloc[exit_i])
    ret = (exit_close / entry_close - 1) * 100

    # align QQQ to the window and rebase both to 100 at entry
    bench = _bench()
    bench_map = dict(zip(bench["date"], bench["close"], strict=False))
    bench_entry = bench_map.get(px["date"].iloc[entry_i])
    series = []
    for d, c in zip(window["date"], window["close"], strict=False):
        b = bench_map.get(d)
        series.append({
            "date": d.date().isoformat(),
            "value": round(c / entry_close * 100, 2),
            "bench": round(b / bench_entry * 100, 2) if (b and bench_entry) else None,
        })
    bench_exit = bench_map.get(px["date"].iloc[exit_i])
    bench_ret = ((bench_exit / bench_entry - 1) * 100) if (bench_entry and bench_exit) else None

    ok, verb = _verdict(signal, ret, bench_ret)
    company, sector = _company(ticker)
    return {
        "id": f"{ticker}-{date_str}",
        "signal": signal,
        "ticker": ticker,
        "company": company,
        "sector": sector,
        "entryDate": px["date"].iloc[entry_i].date().isoformat(),
        "exitDate": px["date"].iloc[exit_i].date().isoformat(),
        "entryPrice": round(entry_close, 2),
        "exitPrice": round(exit_close, 2),
        "ret": round(ret, 1),
        "benchRet": round(bench_ret, 1) if bench_ret is not None else None,
        "notional": NOTIONAL,
        "endValue": round(NOTIONAL * (1 + ret / 100)),
        "holdDays": HORIZON,
        "conviction": conviction,
        "drivers": drivers,
        "volRegime": _vol_regime(ticker, entry_date),
        "correct": ok,
        "verdictVerb": verb,
        "entryIndex": entry_i - lo,
        "exitIndex": exit_i - lo,
        "series": series,
    }


def build_scenarios() -> list[dict]:
    out = []
    for ticker, date_str in _PICKS:
        try:
            sc = _scenario(ticker, date_str)
        except Exception:
            sc = None
        if sc:
            out.append(sc)
    return out
