"""
Training-window sensitivity.

Walk-forward quietly assumes "all prior history" is the right amount to train on.
It usually isn't: too short and the model only knows the latest regime, too long and
it's anchored to markets that no longer exist. This runs the same anchored weekly
scheme with capped look-backs (2-5 years and expanding) and reports not just the OOS
Sharpe but how *stable* each window is — peak Sharpe on a jumpy series is worth less
than a slightly lower one you can actually rely on week to week.

All variants are aligned to predict the *same* set of weeks (we start once the
longest look-back has full history), so the comparison is apples-to-apples.

    python -m ml.research.window_comparison

Reads data/processed/features.parquet, writes data/research/window_comparison.json.
"""
from __future__ import annotations

import json
from datetime import date

import pandas as pd

from ml import paths
from ml.labels.outperformance import make_labels
from ml.research.rolling_window import (
    _basket_series,
    _new_model,
    rolling_window_oos,
    series_metrics,
)
from ml.training.walk_forward import classification_metrics

# trading-day look-backs; None = anchored/expanding
WINDOWS: dict[str, int | None] = {
    "2y": 504, "3y": 756, "4y": 1008, "5y": 1260, "expanding": None,
}
SWEEP_STEP = 10  # biweekly — five full refit sweeps stay tractable


def compare_windows(
    d: pd.DataFrame,
    windows: dict[str, int | None] = WINDOWS,
    step: int = SWEEP_STEP,
    start_idx: int | None = None,
    model_factory=_new_model,
    feature_cols: list[str] | None = None,
) -> dict:
    """Score each training-window length over an identical evaluation span."""
    finite = [v for v in windows.values() if v]
    align = start_idx if start_idx is not None else (max(finite) if finite else 252)

    results: dict[str, dict] = {}
    for name, lookback in windows.items():
        oos, _ = rolling_window_oos(
            d, lookback=lookback, step=step, start_idx=align,
            model_factory=model_factory, feature_cols=feature_cols, track_drift=False,
        )
        if oos.empty:
            continue
        results[name] = {**classification_metrics(oos), **series_metrics(_basket_series(oos))}

    best = max(results, key=lambda k: results[k]["sharpe"]) if results else None
    steadiest = min(results, key=lambda k: results[k]["volatility"]) if results else None
    return {
        "note": "Anchored weekly scheme with capped look-backs, all aligned to the "
                "same evaluation weeks. 'volatility' is annualised weekly dispersion "
                "(lower = steadier).",
        "generatedAt": date.today().isoformat(),
        "evalStartIdx": align,
        "step": step,
        "windows": results,
        "bestBySharpe": best,
        "steadiestByVol": steadiest,
    }


def main() -> None:
    if not paths.FEATURES_PATH.exists():
        raise SystemExit("No features.parquet. Run `python -m ml.features.build` first.")
    d = make_labels(pd.read_parquet(paths.FEATURES_PATH))
    result = compare_windows(d)

    print(f"{'window':<10} {'sharpe':>7} {'cagr':>7} {'maxDD':>7} {'vol':>7} {'hit':>6}")
    for name, m in result["windows"].items():
        print(f"{name:<10} {m['sharpe']:>7} {m['cagr'] * 100:>6.1f}% "
              f"{m['maxDrawdown'] * 100:>6.1f}% {m['volatility'] * 100:>6.1f}% "
              f"{m['hitRate'] * 100:>5.0f}%")
    print(f"best Sharpe: {result['bestBySharpe']}   steadiest: {result['steadiestByVol']}")

    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    out_path = paths.RESEARCH_DIR / "window_comparison.json"
    out_path.write_text(json.dumps(result, indent=2))
    print(f"Saved {out_path.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
