"""
Pipeline orchestrator.

One entry point that runs the ML stages in order, with structured logging, a
data-quality gate between feature-build and training, and stage selection so a
scheduler can run just the cheap daily path (features → validate → score → drift)
or the full weekly retrain.

    python -m ml.pipeline                      # full run, ingest → drift
    python -m ml.pipeline --start features     # skip the slow re-download
    python -m ml.pipeline --only validate,score,drift
    python -m ml.pipeline --dry-run            # print the plan, run nothing

The validate stage is the gate: if features.parquet fails a critical check, the
run aborts before a single model is trained on bad data. A health report is
written to data/research/data_health.json for the API to surface.
"""
from __future__ import annotations

import argparse
import json
import logging
import time

import pandas as pd

from ml import paths
from ml.features.build import FEATURE_COLS
from ml.validation import gate, validate_frame

log = logging.getLogger("pipeline")

STAGE_ORDER = ["ingest", "features", "validate", "train", "score", "drift"]


def _ingest() -> dict:
    from ml.ingestion import download
    download.main()
    return {}


def _features() -> dict:
    from ml.features import build
    build.main()
    return {}


def _validate() -> dict:
    """Data-quality gate: refuse to go further if features.parquet is unhealthy."""
    df = pd.read_parquet(paths.FEATURES_PATH)
    report = validate_frame(
        df,
        artifact="features",
        required_columns=["date", "ticker", *FEATURE_COLS],
        min_rows=10_000,
        finite_columns=FEATURE_COLS,
        date_column="date",
        max_staleness_days=10,
    )
    paths.RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    (paths.RESEARCH_DIR / "data_health.json").write_text(json.dumps(report.to_dict(), indent=2))
    for w in report.warnings:
        log.warning("data-quality warning — %s: %s", w.name, w.detail)
    gate(report)  # raises DataQualityError on any critical failure
    return report.to_dict()


def _train() -> dict:
    from ml.training import walk_forward
    walk_forward.main()
    return {}


def _score() -> dict:
    from ml.inference import score
    score.main()
    return {}


def _drift() -> dict:
    from ml.research import drift
    drift.main()
    return {}


STAGES = {
    "ingest": _ingest,
    "features": _features,
    "validate": _validate,
    "train": _train,
    "score": _score,
    "drift": _drift,
}


def plan(only: list[str] | None = None, skip: list[str] | None = None,
         start: str | None = None) -> list[str]:
    """Resolve which stages to run, preserving canonical order."""
    stages = list(STAGE_ORDER)
    if start:
        if start not in stages:
            raise ValueError(f"unknown start stage: {start}")
        stages = stages[stages.index(start):]
    if only:
        stages = [s for s in stages if s in set(only)]
    if skip:
        stages = [s for s in stages if s not in set(skip)]
    return stages


def run(stages: list[str], dry_run: bool = False) -> dict:
    results: dict[str, dict] = {}
    for s in stages:
        if dry_run:
            log.info("plan: %s", s)
            results[s] = {"planned": True}
            continue
        start = time.time()
        log.info("→ %s", s)
        out = STAGES[s]()
        elapsed = round(time.time() - start, 1)
        results[s] = {"ok": True, "seconds": elapsed, **(out or {})}
        log.info("✓ %s (%.1fs)", s, elapsed)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the QuantML pipeline.")
    parser.add_argument("--only", help="comma-separated stages to run")
    parser.add_argument("--skip", help="comma-separated stages to skip")
    parser.add_argument("--start", help="start from this stage (skip earlier ones)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    parser.add_argument("--quiet", action="store_true", help="warnings and errors only")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    only = args.only.split(",") if args.only else None
    skip = args.skip.split(",") if args.skip else None
    stages = plan(only=only, skip=skip, start=args.start)
    log.info("pipeline plan: %s", " → ".join(stages) or "(nothing)")
    run(stages, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
