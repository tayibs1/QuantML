"""
Signal-replay scenarios for the dashboard's interactive demo.

Reconstructs a handful of real trades from the walk-forward backtest ledger: the
model's BUY at entry, the daily price path it played out over, and the realized
P&L at exit. Everything is read straight from the artifacts (the backtest trade
ledger, OHLCV, and the cached OOS predictions for the model's conviction at
entry), so the replay shows real history rather than a scripted animation.
"""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd
from config import settings

_LOOKBACK = 30  # trading days of context drawn before the entry
_POST = 7       # trading days shown after the exit ("what happened next")


@lru_cache(maxsize=1)
def _ohlcv() -> pd.DataFrame:
    df = pd.read_parquet(settings.data_dir / "raw" / "ohlcv.parquet")
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values(["ticker", "date"])


@lru_cache(maxsize=1)
def _oos() -> pd.DataFrame | None:
    path = settings.data_dir / "backtests" / "oos_predictions.parquet"
    if not path.exists():
        return None
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    return df


def _vol_regime(vol_z: float) -> str:
    if vol_z < -0.5:
        return "Low"
    if vol_z < 0.5:
        return "Moderate"
    if vol_z < 1.5:
        return "High"
    return "Elevated"


def _name(ticker: str) -> tuple[str, str]:
    try:
        import sys
        from pathlib import Path
        root = str(Path(__file__).resolve().parents[2])
        if root not in sys.path:
            sys.path.insert(0, root)
        from ml.universe import company, sector
        return company(ticker), sector(ticker)
    except Exception:
        return ticker, "—"


def _scenario(trade: dict) -> dict | None:
    ohlcv = _ohlcv()
    ticker = trade["ticker"]
    exit_date = pd.Timestamp(trade["date"])
    entry_date = exit_date - pd.Timedelta(days=int(trade["hold"]))

    s = ohlcv[ohlcv["ticker"] == ticker][["date", "close"]].reset_index(drop=True)
    if s.empty:
        return None
    entry_i = int((s["date"] - entry_date).abs().idxmin())
    exit_i = int((s["date"] - exit_date).abs().idxmin())
    if exit_i <= entry_i:
        return None

    lo = max(0, entry_i - _LOOKBACK)
    hi = min(len(s) - 1, exit_i + _POST)
    window = s.iloc[lo : hi + 1]
    series = [
        {"date": d.date().isoformat(), "close": round(float(c), 2)}
        for d, c in zip(window["date"], window["close"], strict=False)
    ]

    p_buy = None
    vol_regime = None
    oos = _oos()
    if oos is not None:
        o = oos[(oos["ticker"] == ticker) & (oos["date"] <= entry_date)].sort_values("date")
        if len(o):
            p_buy = round(float(o["p_buy"].iloc[-1]), 4)
            vol_regime = _vol_regime(float(o["vol_z"].iloc[-1]))

    company, sector = _name(ticker)
    return {
        "id": trade["id"],
        "ticker": ticker,
        "company": company,
        "sector": sector,
        "entryDate": s["date"].iloc[entry_i].date().isoformat(),
        "exitDate": s["date"].iloc[exit_i].date().isoformat(),
        "entryPrice": float(trade["entry"]),
        "exitPrice": float(trade["exit"]),
        "ret": float(trade["ret"]),
        "pnl": float(trade["pnl"]),
        "holdDays": int(trade["hold"]),
        "pBuy": p_buy,
        "volRegime": vol_regime,
        "entryIndex": entry_i - lo,
        "exitIndex": exit_i - lo,
        "series": series,
    }


def build_scenarios(max_winners: int = 4) -> list[dict]:
    """The strongest real winners plus the single worst loss, so it isn't cherry-picked."""
    bt_path = settings.data_dir / "backtests" / "latest.json"
    if not bt_path.exists():
        return []
    try:
        trades = json.loads(bt_path.read_text()).get("trades", [])
    except (json.JSONDecodeError, OSError):
        return []

    winners = sorted((t for t in trades if t.get("ret", 0) >= 15), key=lambda t: -t["ret"])
    losers = sorted((t for t in trades if t.get("ret", 0) <= -8), key=lambda t: t["ret"])

    out = []
    for t in [*winners[:max_winners], *losers[:1]]:
        try:
            sc = _scenario(t)
        except Exception:
            sc = None
        if sc:
            out.append(sc)
    return out
