"""
Stage 2 — Feature engineering.

Computes ~24 causal features per name (no future bars), then standardizes them
**cross-sectionally per date** (z-score across the universe) so the model learns
relative, not absolute, signals. Also attaches the 5-day forward-return target.

    python -m ml.features.build

`compute_features()` is imported by both training and inference, guaranteeing the
exact same transform is applied live as in training.

Output:
    data/processed/features.parquet   [date, ticker, <features…>, fwd_ret_5]
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import paths

FORWARD_HORIZON = 5  # predict the 5-day-ahead return

# Feature column -> human-readable label (used for the UI "drivers" chips).
FEATURE_LABELS: dict[str, str] = {
    "ret_5": "5-day momentum",
    "ret_20": "20-day momentum",
    "ret_60": "60-day momentum",
    "ret_120": "120-day momentum",
    "sma20_dist": "Distance from 20d MA",
    "sma50_dist": "Distance from 50d MA",
    "sma200_dist": "Distance from 200d MA",
    "rsi_14": "RSI (14)",
    "vol_20": "20-day volatility",
    "vol_60": "60-day volatility",
    "vol_of_vol": "Volatility of volatility",
    "atr_pct": "ATR % of price",
    "bb_pctb": "Bollinger %b",
    "macd_hist": "MACD histogram",
    "volume_z": "Volume z-score",
    "dollar_vol_z": "Dollar-volume z-score",
    "obv_slope": "On-balance-volume slope",
    "dist_52w_high": "Distance from 52w high",
    "dist_52w_low": "Distance from 52w low",
    "ret_skew_20": "Return skew (20d)",
    "ret_kurt_20": "Return kurtosis (20d)",
    "gap": "Overnight gap",
    "intraday_range": "Intraday range",
    "rel_strength_20": "Relative strength (20d)",
}
FEATURE_COLS: list[str] = list(FEATURE_LABELS.keys())


def _rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(n).mean()
    loss = (-delta.clip(upper=0)).rolling(n).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def _atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev_close = df["close"].shift(1)
    tr = pd.concat(
        [
            df["high"] - df["low"],
            (df["high"] - prev_close).abs(),
            (df["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(n).mean()


def _per_ticker(df: pd.DataFrame) -> pd.DataFrame:
    """Causal time-series features for a single name (sorted by date)."""
    # reset_index is essential: indicator Series must share an index with `out`,
    # otherwise the column assignments below align to NaN.
    df = df.sort_values("date").reset_index(drop=True).copy()
    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]
    ret1 = close.pct_change()

    out = pd.DataFrame({"date": df["date"].values, "ticker": df["ticker"].values})

    # Momentum
    out["ret_5"] = close.pct_change(5)
    out["ret_20"] = close.pct_change(20)
    out["ret_60"] = close.pct_change(60)
    out["ret_120"] = close.pct_change(120)

    # Trend / moving-average distance
    out["sma20_dist"] = close / close.rolling(20).mean() - 1
    out["sma50_dist"] = close / close.rolling(50).mean() - 1
    out["sma200_dist"] = close / close.rolling(200).mean() - 1

    # Oscillators
    out["rsi_14"] = _rsi(close, 14)
    ma20 = close.rolling(20).mean()
    sd20 = close.rolling(20).std()
    out["bb_pctb"] = (close - (ma20 - 2 * sd20)) / (4 * sd20)
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()) / close

    # Volatility
    out["vol_20"] = ret1.rolling(20).std() * np.sqrt(252)
    out["vol_60"] = ret1.rolling(60).std() * np.sqrt(252)
    out["vol_of_vol"] = out["vol_20"].rolling(20).std()
    out["atr_pct"] = _atr(df, 14) / close

    # Volume
    out["volume_z"] = (vol - vol.rolling(20).mean()) / vol.rolling(20).std()
    dollar = (close * vol).replace(0, np.nan)
    logdollar = np.log(dollar)
    out["dollar_vol_z"] = (logdollar - logdollar.rolling(60).mean()) / logdollar.rolling(60).std()
    obv = (np.sign(ret1).fillna(0) * vol).cumsum()
    out["obv_slope"] = (obv - obv.shift(20)) / (vol.rolling(20).mean() * 20)

    # Range / extremes
    out["dist_52w_high"] = close / close.rolling(252).max() - 1
    out["dist_52w_low"] = close / close.rolling(252).min() - 1
    out["ret_skew_20"] = ret1.rolling(20).skew()
    out["ret_kurt_20"] = ret1.rolling(20).kurt()
    out["gap"] = df["open"] / close.shift(1) - 1
    out["intraday_range"] = (high - low) / close
    out["rel_strength_20"] = out["ret_20"]  # vs-universe handled by x-sec z-score

    # Target: forward 5-day return (NaN for the last HORIZON rows)
    out["fwd_ret_5"] = close.shift(-FORWARD_HORIZON) / close - 1
    return out


def _cross_sectional_zscore(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Z-score each feature across the universe within each date, clipped to ±5."""
    g = df.groupby("date")
    for c in cols:
        mu = g[c].transform("mean")
        sd = g[c].transform("std").replace(0, np.nan)
        df[c] = ((df[c] - mu) / sd).clip(-5, 5)
    return df


def compute_features(ohlcv: pd.DataFrame, min_names: int = 10) -> pd.DataFrame:
    """Full feature pipeline: per-name causal features → cross-sectional z-score.

    Reused verbatim by training and inference.
    """
    parts = [_per_ticker(g) for _, g in ohlcv.groupby("ticker", sort=False)]
    feats = pd.concat(parts, ignore_index=True)

    # Need all features present (drops per-name warmup rows). Target may be NaN
    # (latest rows) — that's fine; training drops them, inference uses them.
    feats = feats.dropna(subset=FEATURE_COLS).reset_index(drop=True)
    feats = _cross_sectional_zscore(feats, FEATURE_COLS)
    feats = feats.dropna(subset=FEATURE_COLS).reset_index(drop=True)

    # Drop sparse dates (too few names for a meaningful cross-section)
    counts = feats.groupby("date")["ticker"].transform("count")
    feats = feats[counts >= min_names].reset_index(drop=True)
    return feats.sort_values(["date", "ticker"]).reset_index(drop=True)


def main() -> None:
    paths.ensure_dirs()
    if not paths.OHLCV_PATH.exists():
        raise SystemExit("Run `python -m ml.ingestion.download` first.")
    ohlcv = pd.read_parquet(paths.OHLCV_PATH)
    feats = compute_features(ohlcv)
    feats.to_parquet(paths.FEATURES_PATH, index=False)
    labelled = feats.dropna(subset=["fwd_ret_5"])
    print(
        f"Features: {len(feats):,} rows · {len(FEATURE_COLS)} features · "
        f"{feats['ticker'].nunique()} names · "
        f"{feats['date'].min().date()} … {feats['date'].max().date()}\n"
        f"Labelled (has target): {len(labelled):,} rows\n"
        f"Saved {paths.FEATURES_PATH.relative_to(paths.REPO_ROOT)}"
    )


if __name__ == "__main__":
    main()
