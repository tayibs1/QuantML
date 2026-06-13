"""Data-quality gates: the pipeline must refuse to promote bad artifacts."""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from ml.validation import DataQualityError, gate, validate_frame


def _frame(rows: int = 100) -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=rows, freq="D"),
        "ticker": ["AAA"] * rows,
        "feat": np.linspace(-1, 1, rows),
    })


def test_clean_frame_passes():
    report = validate_frame(
        _frame(), artifact="features",
        required_columns=["date", "ticker", "feat"], min_rows=50,
        finite_columns=["feat"],
    )
    assert report.ok
    assert report.failures == []


def test_missing_required_column_is_critical():
    report = validate_frame(
        _frame(), artifact="features",
        required_columns=["date", "ticker", "label"],  # label absent
    )
    assert not report.ok
    assert any(c.name == "required_columns" for c in report.failures)


def test_too_few_rows_is_critical():
    report = validate_frame(
        _frame(rows=10), artifact="features",
        required_columns=["date"], min_rows=50,
    )
    assert not report.ok


def test_non_finite_values_are_critical():
    df = _frame()
    df.loc[5, "feat"] = np.inf
    report = validate_frame(
        df, artifact="features", required_columns=["feat"], finite_columns=["feat"],
    )
    assert not report.ok
    assert any(c.name == "finite:feat" for c in report.failures)


def test_nulls_warn_but_do_not_block():
    df = _frame()
    df.loc[3, "ticker"] = None
    report = validate_frame(
        df, artifact="features", required_columns=["ticker"], non_null_columns=["ticker"],
    )
    assert report.ok  # nulls are a warning, not a blocker
    assert any(c.name == "non_null:ticker" for c in report.warnings)


def test_staleness_warns_when_artifact_is_old():
    report = validate_frame(
        _frame(rows=30), artifact="features", required_columns=["date"],
        date_column="date", max_staleness_days=7, today=date(2025, 1, 1),
    )
    assert report.ok  # staleness is a warning
    assert any(c.name == "freshness" for c in report.warnings)


def test_gate_raises_on_critical_failure():
    report = validate_frame(
        pd.DataFrame(), artifact="features", required_columns=["date"],
    )
    with pytest.raises(DataQualityError):
        gate(report)


def test_gate_passes_clean_report():
    report = validate_frame(_frame(), artifact="features", required_columns=["date"])
    assert gate(report) is report
