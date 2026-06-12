"""
Where does the edge actually live?

A single headline Sharpe hides as much as it shows. This breaks the out-of-sample
BUY basket down two ways - by calendar year, and by market regime (is QQQ above or
below its 200-day average) - so you can see the years and conditions where the
model earns its keep and the ones where it just tracks the tape. Being able to
point at the bad years is more convincing than a clean average.

    python -m ml.research.regime

Reads the cached OOS predictions the backtest already uses, writes
data/research/regime.json.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from ml import paths
from ml.labels.outperformance import BUY

# 5-day horizon, de-overlapped -> ~50 independent observations a year
PERIODS_PER_YEAR = 252 / 5
SMA_WINDOW = 200


def basket_returns(oos: pd.DataFrame, buy_class: int = BUY) -> pd.Series:
    """Non-overlapping daily BUY-basket forward returns, date-indexed.

    Same construction as the walk-forward strategy metric: average the 5-day
    forward return across the names predicted BUY each date, then sample every
    fifth date so the overlapping horizons don't double-count.
    """
    buy = oos[oos["pred"] == buy_class]
    if buy.empty:
        return pd.Series(dtype=float)
    daily = buy.groupby("date")["fwd_ret_5"].mean().sort_index()
    return daily.iloc[::5]


def _sharpe(r: pd.Series) -> float:
    if len(r) < 3 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * np.sqrt(PERIODS_PER_YEAR))


def _hit_rate(r: pd.Series) -> float:
    return float((r > 0).mean()) if len(r) else 0.0


def by_year(oos: pd.DataFrame, bench_year_ret: dict[int, float] | None = None) -> list[dict]:
    """One row per calendar year: Sharpe, mean 5d return, hit rate, n."""
    r = basket_returns(oos)
    if r.empty:
        return []
    df = r.rename("ret").reset_index()
    df["year"] = pd.to_datetime(df["date"]).dt.year
    out = []
    for year, g in df.groupby("year"):
        row = {
            "year": int(year),
            "sharpe": round(_sharpe(g["ret"]), 2),
            "meanReturn5d": round(float(g["ret"].mean()) * 100, 3),
            "hitRate": round(_hit_rate(g["ret"]), 4),
            "n": int(len(g)),
        }
        if bench_year_ret and year in bench_year_ret:
            row["benchReturn"] = round(bench_year_ret[year] * 100, 1)
        out.append(row)
    return out


def benchmark_regime(benchmark: pd.DataFrame) -> pd.Series:
    """Bull when the benchmark closes above its 200d average, else Bear."""
    b = benchmark.sort_values("date").copy()
    sma = b["close"].rolling(SMA_WINDOW).mean()
    regime = np.where(b["close"] >= sma, "Bull", "Bear")
    return pd.Series(regime, index=pd.to_datetime(b["date"]))


def by_regime(oos: pd.DataFrame, benchmark: pd.DataFrame) -> list[dict]:
    """Split the basket returns by the market regime in force on each date."""
    r = basket_returns(oos)
    if r.empty:
        return []
    regime = benchmark_regime(benchmark)
    df = r.rename("ret").reset_index()
    df["date"] = pd.to_datetime(df["date"])
    df["regime"] = df["date"].map(regime).fillna("Bull")
    out = []
    for name in ("Bull", "Bear"):
        g = df[df["regime"] == name]
        if g.empty:
            continue
        out.append({
            "regime": name,
            "sharpe": round(_sharpe(g["ret"]), 2),
            "meanReturn5d": round(float(g["ret"].mean()) * 100, 3),
            "hitRate": round(_hit_rate(g["ret"]), 4),
            "n": int(len(g)),
        })
    return out


def _benchmark_year_returns(benchmark: pd.DataFrame) -> dict[int, float]:
    b = benchmark.sort_values("date").copy()
    b["year"] = pd.to_datetime(b["date"]).dt.year
    out = {}
    for year, g in b.groupby("year"):
        first, last = g["close"].iloc[0], g["close"].iloc[-1]
        out[int(year)] = float(last / first - 1) if first else 0.0
    return out


def main() -> None:
    oos_path = paths.DATA_DIR / "backtests" / "oos_predictions.parquet"
    if not oos_path.exists():
        raise SystemExit("No OOS predictions. Run `python -m backtesting.engine` first.")
    oos = pd.read_parquet(oos_path)

    bench = pd.read_parquet(paths.BENCHMARK_PATH) if paths.BENCHMARK_PATH.exists() else None
    bench_year = _benchmark_year_returns(bench) if bench is not None else None

    years = by_year(oos, bench_year)
    regimes = by_regime(oos, bench) if bench is not None else []

    print("By year:")
    for y in years:
        bench_str = f"  (QQQ {y['benchReturn']:+}%)" if "benchReturn" in y else ""
        print(f"  {y['year']}  sharpe={y['sharpe']:>5}  mean5d={y['meanReturn5d']:>6}%  "
              f"hit={y['hitRate'] * 100:.1f}%  n={y['n']}{bench_str}")
    print("By regime:")
    for g in regimes:
        print(f"  {g['regime']:4}  sharpe={g['sharpe']:>5}  mean5d={g['meanReturn5d']:>6}%  "
              f"hit={g['hitRate'] * 100:.1f}%  n={g['n']}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "regime.json"
    out_path.write_text(json.dumps({
        "note": "OOS BUY-basket, non-overlapping 5d returns. Signal-quality "
                "(frictionless), not net-of-cost.",
        "byYear": years,
        "byRegime": regimes,
    }, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
