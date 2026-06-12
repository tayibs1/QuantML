"""
Production label: cross-sectional outperformance.

For each (date t0, ticker) we open a bet over an h-day horizon ending at
t1 = t0 + h trading days, scored by the h-day forward return. Within each date
we rank the names against each other:

    BUY   (2)  forward return in the top tercile of the universe that day
    AVOID (0)  bottom tercile
    HOLD  (1)  middle tercile

Ranking names against their peers is a lot steadier than trying to predict an
absolute return. Labels are defined in exactly one place - ml.training pulls
make_labels from here so the two can't drift apart.

build_label_artifacts writes two files:

    labels.parquet   date, ticker, label, fwd_ret, t1, weight
    events.parquet   date, ticker, t1, horizon, fwd_ret, rank_pct,
                     outperf_universe, outperf_benchmark

weight is an average-uniqueness sample weight (AFML ch.4). Overlapping h-day
windows on the same name aren't independent, so each label gets discounted by
how much its life overlaps its neighbours. Normalised to mean 1 so it drops
straight into a learner's sample_weight.

    python -m ml.labels.outperformance
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ml import paths

# class indices, shared across the pipeline
AVOID, HOLD, BUY = 0, 1, 2
CLASS_TO_SIGNAL = {AVOID: "AVOID", HOLD: "HOLD", BUY: "BUY"}

# forward horizon in trading days; has to line up with the fwd_ret_5 feature
LABEL_HORIZON = 5

# tercile cut points
_LOWER, _UPPER = 1 / 3, 2 / 3
_FWD_COL = "fwd_ret_5"


def make_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the cross-sectional tercile label to a feature frame.

    Deterministic. Drops rows that don't have a realised forward return yet
    (the last LABEL_HORIZON bars per name), which is what training wants anyway.
    """
    d = df.dropna(subset=[_FWD_COL]).copy()
    pct = d.groupby("date")[_FWD_COL].rank(pct=True)
    d["label"] = np.where(pct >= _UPPER, BUY, np.where(pct <= _LOWER, AVOID, HOLD))
    return d


def _event_end(d: pd.DataFrame) -> pd.Series:
    """t1 = the date LABEL_HORIZON trading bars ahead, per ticker."""
    return d.sort_values(["ticker", "date"]).groupby("ticker")["date"].shift(-LABEL_HORIZON)


def _benchmark_forward_return(benchmark: pd.DataFrame) -> pd.Series:
    """date -> QQQ h-day forward return, for outperformance-vs-market."""
    b = benchmark.sort_values("date").set_index("date")["close"]
    fwd = b.shift(-LABEL_HORIZON) / b - 1.0
    return fwd


def average_uniqueness(events: pd.DataFrame) -> pd.Series:
    """Concurrency-based sample weights (mean-normalised), indexed like events.

    Label i lives over bars [i, i+h]. Concurrency at a bar = how many labels are
    alive there; a label's uniqueness is the mean of 1/concurrency over its life.
    With a fixed horizon almost everything overlaps, so this pulls the
    heavily-overlapping labels down and the effective sample size starts to
    reflect bets that are actually independent.
    """
    weights = pd.Series(1.0, index=events.index)
    h = LABEL_HORIZON
    for _, grp in events.groupby("ticker", sort=False):
        idx = grp.sort_values("date").index.to_numpy()
        n = len(idx)
        if n == 0:
            continue
        conc = np.zeros(n)
        spans = [(i, min(i + h, n - 1)) for i in range(n)]
        for i, j in spans:
            conc[i : j + 1] += 1.0
        for k, (i, j) in enumerate(spans):
            weights.loc[idx[k]] = float(np.mean(1.0 / conc[i : j + 1]))
    mean = weights.mean()
    return weights / mean if mean > 0 else weights


def build_label_artifacts(
    features: pd.DataFrame,
    benchmark: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build (labels_df, events_df): the explicit Y / T / W for the problem."""
    d = make_labels(features)
    d = d.assign(t1=_event_end(d))

    rank_pct = d.groupby("date")[_FWD_COL].rank(pct=True)
    universe_mean = d.groupby("date")[_FWD_COL].transform("mean")
    outperf_universe = d[_FWD_COL] - universe_mean

    if benchmark is not None:
        bench_fwd = _benchmark_forward_return(benchmark)
        outperf_bench = d[_FWD_COL] - d["date"].map(bench_fwd)
    else:
        outperf_bench = pd.Series(np.nan, index=d.index)

    events = pd.DataFrame({
        "date": d["date"].values,
        "ticker": d["ticker"].values,
        "t1": d["t1"].values,
        "horizon": LABEL_HORIZON,
        "fwd_ret": d[_FWD_COL].round(6).values,
        "rank_pct": rank_pct.round(4).values,
        "outperf_universe": outperf_universe.round(6).values,
        "outperf_benchmark": outperf_bench.round(6).values,
    })
    events = events.dropna(subset=["t1"]).reset_index(drop=True)

    weight = average_uniqueness(events)
    events["weight"] = weight.round(4).values

    # map the label back onto each event by (date, ticker); survives the row
    # drops and reindexing above
    label_map = d.set_index(["date", "ticker"])["label"]
    labels = events[["date", "ticker", "t1", "fwd_ret", "weight"]].copy()
    labels["label"] = [
        int(label_map.get((row.date, row.ticker), HOLD))
        for row in events.itertuples(index=False)
    ]
    labels = labels[["date", "ticker", "label", "fwd_ret", "t1", "weight"]]
    return labels, events


def main() -> None:
    paths.ensure_dirs()
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("Run `python -m ml.features.build` first.")
    features = pd.read_parquet(paths.FEATURES_PATH)
    benchmark = (
        pd.read_parquet(paths.BENCHMARK_PATH) if paths.BENCHMARK_PATH.exists() else None
    )

    labels, events = build_label_artifacts(features, benchmark)
    labels.to_parquet(paths.LABELS_PATH, index=False)
    events.to_parquet(paths.EVENTS_PATH, index=False)

    dist = labels["label"].value_counts().reindex([BUY, HOLD, AVOID]).fillna(0).astype(int)
    print(
        f"Labels: {len(labels):,} events · {labels['ticker'].nunique()} names · "
        f"{labels['date'].min().date()} … {labels['date'].max().date()}\n"
        f"  class mix  BUY {dist[BUY]:,}  HOLD {dist[HOLD]:,}  AVOID {dist[AVOID]:,}\n"
        f"  weight     mean {labels['weight'].mean():.3f}  "
        f"min {labels['weight'].min():.3f}  max {labels['weight'].max():.3f}\n"
        f"  outperf    vs-universe μ {events['outperf_universe'].mean():+.4f}  "
        f"vs-QQQ μ {events['outperf_benchmark'].mean():+.4f}\n"
        f"  saved      {paths.LABELS_PATH.relative_to(paths.REPO_ROOT)} + "
        f"{paths.EVENTS_PATH.name}"
    )


if __name__ == "__main__":
    main()
