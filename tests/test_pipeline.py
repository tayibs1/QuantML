"""Pipeline orchestration: stage selection and dry-run plumbing."""
from __future__ import annotations

import pytest

from ml.pipeline import STAGE_ORDER, plan, run


def test_full_plan_is_canonical_order():
    assert plan() == STAGE_ORDER


def test_start_skips_earlier_stages():
    stages = plan(start="features")
    assert stages[0] == "features"
    assert "ingest" not in stages


def test_only_filters_to_requested_stages_in_order():
    stages = plan(only=["score", "validate", "drift"])
    assert stages == ["validate", "score", "drift"]  # canonical order preserved


def test_skip_removes_stages():
    assert "train" not in plan(skip=["train"])


def test_unknown_start_raises():
    with pytest.raises(ValueError):
        plan(start="nope")


def test_dry_run_executes_no_stage():
    # A dry run must never import/run a stage body — just report the plan.
    results = run(["ingest", "train", "score"], dry_run=True)
    assert all(v == {"planned": True} for v in results.values())
    assert list(results) == ["ingest", "train", "score"]
