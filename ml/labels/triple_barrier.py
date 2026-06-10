"""
Triple-barrier labelling — research-grade alternative (López de Prado, AFML §3).

Status: **scaffold.** Implemented for a single price series and runnable as a demo,
but deliberately *not* wired into the production training pipeline, which uses the
cross-sectional `outperformance` label. Promoting this to production would also
mean adding meta-labelling and event sampling (§3.6, §3.8) — future work.

Idea
----
Instead of a fixed h-day horizon, each bet is closed by whichever of three barriers
is touched first:

    upper  (profit-take) : price * (1 + pt · σ_t)      → label +1
    lower  (stop-loss)   : price * (1 - sl · σ_t)      → label -1
    vertical (time-out)  : t0 + max_horizon bars       → label  0 (or sign of ret)

Barrier widths scale with a rolling volatility estimate σ_t, so the labels adapt to
each name's regime rather than imposing one return threshold on everything. The
result is a label whose *event time* t1 is data-dependent — exactly the structure
the sample-weighting in `outperformance.average_uniqueness` is designed to handle.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_volatility(close: pd.Series, span: int = 20) -> pd.Series:
    """Exponentially-weighted volatility of daily returns (barrier scale σ_t)."""
    returns = close.pct_change()
    return returns.ewm(span=span).std()


def apply_triple_barrier(
    close: pd.Series,
    vol: pd.Series,
    pt: float = 2.0,
    sl: float = 2.0,
    max_horizon: int = 10,
) -> pd.DataFrame:
    """First-touch labelling for every bar of a single name's close series.

    Returns a frame indexed by event start t0 with columns:
        t1     — bar at which the first barrier was touched (or the time-out bar)
        ret    — realised return from t0 to t1
        label  — +1 upper, -1 lower, 0 time-out
        touch  — which barrier closed the bet ('pt' | 'sl' | 'time')
    """
    close = close.sort_index()
    idx = close.index
    n = len(idx)
    rows = []
    for i in range(n):
        sigma = vol.iloc[i]
        if not np.isfinite(sigma) or sigma <= 0:
            continue
        p0 = close.iloc[i]
        up, dn = p0 * (1 + pt * sigma), p0 * (1 - sl * sigma)
        end = min(i + max_horizon, n - 1)

        touch, hit = "time", end
        for j in range(i + 1, end + 1):
            pj = close.iloc[j]
            if pj >= up:
                touch, hit = "pt", j
                break
            if pj <= dn:
                touch, hit = "sl", j
                break

        ret = close.iloc[hit] / p0 - 1.0
        label = 1 if touch == "pt" else -1 if touch == "sl" else 0
        rows.append((idx[i], idx[hit], round(float(ret), 6), label, touch))

    return pd.DataFrame(rows, columns=["t0", "t1", "ret", "label", "touch"]).set_index("t0")


def triple_barrier_labels(
    close: pd.Series,
    pt: float = 2.0,
    sl: float = 2.0,
    max_horizon: int = 10,
    vol_span: int = 20,
) -> pd.DataFrame:
    """Convenience wrapper: estimate σ_t then apply the barriers to one series."""
    vol = daily_volatility(close, span=vol_span)
    return apply_triple_barrier(close, vol, pt=pt, sl=sl, max_horizon=max_horizon)


def main() -> None:
    """Demo on one name so the scaffold is runnable and verifiable."""
    from ml import paths

    if not paths.OHLCV_PATH.exists():
        raise SystemExit("Run `python -m ml.ingestion.download` first.")
    ohlcv = pd.read_parquet(paths.OHLCV_PATH)
    ticker = "NVDA" if (ohlcv["ticker"] == "NVDA").any() else ohlcv["ticker"].iloc[0]
    series = ohlcv[ohlcv["ticker"] == ticker].set_index("date")["close"]

    out = triple_barrier_labels(series)
    mix = out["touch"].value_counts()
    print(
        f"[scaffold] triple-barrier on {ticker}: {len(out):,} events\n"
        f"  touches    pt {int(mix.get('pt', 0)):,}  sl {int(mix.get('sl', 0)):,}  "
        f"time {int(mix.get('time', 0)):,}\n"
        f"  mean ret   {out['ret'].mean():+.4f}   win rate {(out['ret'] > 0).mean():.1%}\n"
        f"  NOTE       experimental — not used by the production pipeline."
    )


if __name__ == "__main__":
    main()
