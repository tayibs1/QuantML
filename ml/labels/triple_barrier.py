"""
Triple-barrier labelling - a research alternative (AFML ch.3).

Scaffold only. Works on a single price series and runs as a demo, but it's not
hooked into the production pipeline (that uses the cross-sectional outperformance
label). Taking this to production would also need meta-labelling and event
sampling, which I haven't done yet.

The idea: instead of a fixed h-day horizon, close each bet at whichever of three
barriers gets hit first.

    upper  (profit-take) : price * (1 + pt * sigma_t)   -> label +1
    lower  (stop-loss)   : price * (1 - sl * sigma_t)   -> label -1
    vertical (time-out)  : t0 + max_horizon bars        -> label  0

Barrier widths scale with a rolling vol estimate sigma_t, so they adapt to each
name's regime instead of forcing one return threshold on everything. The catch
is that the event time t1 becomes data-dependent, which is exactly what the
average-uniqueness weighting in outperformance.py is there to handle.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_volatility(close: pd.Series, span: int = 20) -> pd.Series:
    """EWM volatility of daily returns - this is the sigma_t the barriers scale by."""
    returns = close.pct_change()
    return returns.ewm(span=span).std()


def apply_triple_barrier(
    close: pd.Series,
    vol: pd.Series,
    pt: float = 2.0,
    sl: float = 2.0,
    max_horizon: int = 10,
) -> pd.DataFrame:
    """First-touch labelling for every bar of one name's close series.

    Frame indexed by event start t0:
        t1     bar where the first barrier was touched (or the time-out bar)
        ret    realised return from t0 to t1
        label  +1 upper, -1 lower, 0 time-out
        touch  which barrier closed it ('pt' | 'sl' | 'time')
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
    """Estimate sigma_t, then run the barriers over one series."""
    vol = daily_volatility(close, span=vol_span)
    return apply_triple_barrier(close, vol, pt=pt, sl=sl, max_horizon=max_horizon)


def main() -> None:
    """Demo on a single name so the scaffold actually runs and can be checked."""
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
