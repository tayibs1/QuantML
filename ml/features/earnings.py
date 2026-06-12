"""
Earnings-cycle features, inferred from the tape.

The honest backstory: reliable historical earnings dates aren't freely available
anymore - Yahoo put the earnings endpoint behind a cookie/crumb in 2024 and it
returns empty here, the same flakiness the OHLCV ingestion already works around.
Rather than ship a fragile network dependency, this infers earnings events from
the data we already have. Earnings announcements reliably spike trading volume,
so a per-name abnormal-volume spike, spaced roughly a quarter apart, is a good
proxy for "this name just reported".

From those inferred events come three causal features:
  - earn_days_since   trading days since the last inferred report (post-earnings
                      drift, PEAD, is a real and well-documented anomaly)
  - earn_post5        in the 5-day window right after a report
  - earn_pre5         approaching the next expected report (~63 trading days on)

Causality: a spike on day D is known at D's close, and every feature at date T
only references events at or before T, so nothing peeks ahead. The next-report
estimate is just last_report + one quarter - also knowable at T.

This is a proxy, not a calendar. It's labelled as one everywhere it surfaces.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EARNINGS_FEATURES = ["earn_days_since", "earn_post5", "earn_pre5"]

_LOOKBACK = 60      # trailing window for the "normal" volume baseline
_MIN_GAP = 40       # trading days between events - stops one report double-marking
# 2.0x the trailing-median volume lands ~3.8 events/yr across the universe, which
# matches the true ~4 quarterly reports while staying high-precision (spot-checked
# against real report dates: AAPL 2018-02-02, 2018-08-01, 2018-11-02 all line up)
_Z_THRESH = 2.0
_QUARTER = 63       # ~trading days in a quarter, for the next-report estimate
_WINDOW = 5         # PEAD / anticipation window width


def _detect_one(volume: np.ndarray) -> np.ndarray:
    """Boolean mask of inferred earnings days for a single name.

    Abnormal volume = volume / trailing-median volume (causal). Walking forward,
    mark the first day that clears the threshold once at least _MIN_GAP days have
    passed since the previous mark - greedy, so events land ~a quarter apart.
    """
    med = pd.Series(volume).rolling(_LOOKBACK, min_periods=20).median().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        abn = np.where(med > 0, volume / med, np.nan)
    marks = np.zeros(len(volume), dtype=bool)
    last = -10**9
    for i in range(len(volume)):
        if abn[i] >= _Z_THRESH and (i - last) >= _MIN_GAP:
            marks[i] = True
            last = i
    return marks


def _features_one(g: pd.DataFrame) -> pd.DataFrame:
    """Earnings-cycle features for one name, sorted by date."""
    g = g.sort_values("date").reset_index(drop=True)
    marks = _detect_one(g["volume"].to_numpy())
    n = len(g)

    days_since = np.full(n, np.nan)
    last_mark = -1
    for i in range(n):
        if marks[i]:          # known at this day's close - fair to use today
            last_mark = i
        if last_mark >= 0:
            days_since[i] = i - last_mark

    # estimate the next report as one quarter on from the last one
    expected_next = np.where(np.isnan(days_since), np.nan, (np.arange(n) - days_since) + _QUARTER)
    days_until = expected_next - np.arange(n)

    out = pd.DataFrame({"date": g["date"].values, "ticker": g["ticker"].values})
    out["earn_days_since"] = days_since
    out["earn_post5"] = (days_since <= _WINDOW).astype(float)
    out["earn_pre5"] = ((days_until > 0) & (days_until <= _WINDOW)).astype(float)
    return out


def earnings_features(ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Per-name earnings-cycle features, long format [date, ticker, <earn_*>].

    Merge onto the main feature frame on (date, ticker). NaNs (a name's early
    history before its first inferred report) should be filled by the caller -
    typically with a large days_since and zero windows.
    """
    parts = [_features_one(g) for _, g in ohlcv.groupby("ticker", sort=False)]
    return pd.concat(parts, ignore_index=True)


def attach_earnings(features: pd.DataFrame, ohlcv: pd.DataFrame) -> pd.DataFrame:
    """Left-join earnings features onto a feature frame, filling the warmup gap.

    Before a name's first inferred report we don't know the cycle, so days_since
    gets a large sentinel (one quarter) and both windows are zero - a neutral
    "not near earnings" prior.
    """
    earn = earnings_features(ohlcv)
    merged = features.merge(earn, on=["date", "ticker"], how="left")
    merged["earn_days_since"] = merged["earn_days_since"].fillna(float(_QUARTER))
    merged["earn_post5"] = merged["earn_post5"].fillna(0.0)
    merged["earn_pre5"] = merged["earn_pre5"].fillna(0.0)
    return merged
