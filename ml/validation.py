"""
Data-quality gates for the pipeline.

Every artifact (raw OHLCV, features, the scored cross-section) gets validated
*before* anything downstream is allowed to consume or promote it. The rule is
simple: fail loud, never train or score on bad data. A backtest built on a
silently-truncated feature table is worse than no backtest at all.

Checks are tagged `critical` (block promotion) or `warn` (surface, don't block).
`validate_frame()` returns a structured report; `gate()` turns a failed report
into a raised error. The report is JSON-serialisable so the API can show pipeline
health on the dashboard.

    from ml.validation import validate_frame, gate
    report = validate_frame(df, artifact="features", required_columns=[...], min_rows=10_000)
    gate(report)  # raises DataQualityError if any critical check failed
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date

import numpy as np
import pandas as pd

Severity = str  # "critical" | "warn"


class DataQualityError(RuntimeError):
    """Raised when an artifact fails a critical data-quality check."""


@dataclass
class Check:
    name: str
    passed: bool
    severity: Severity
    detail: str = ""


@dataclass
class ValidationReport:
    artifact: str
    checks: list[Check] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True unless a *critical* check failed (warnings don't block)."""
        return all(c.passed for c in self.checks if c.severity == "critical")

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.severity == "critical"]

    @property
    def warnings(self) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.severity == "warn"]

    def to_dict(self) -> dict:
        return {
            "artifact": self.artifact,
            "ok": self.ok,
            "checks": [asdict(c) for c in self.checks],
            "failures": [c.name for c in self.failures],
            "warnings": [c.name for c in self.warnings],
        }


def validate_frame(
    df: pd.DataFrame,
    *,
    artifact: str,
    required_columns: list[str],
    min_rows: int = 1,
    non_null_columns: list[str] | None = None,
    finite_columns: list[str] | None = None,
    date_column: str | None = None,
    max_staleness_days: int | None = None,
    today: date | None = None,
) -> ValidationReport:
    """Run the standard battery of checks and return a report.

    Critical: non-empty, required columns present, row count, finite numerics.
    Warn:     null values in key columns, artifact freshness (staleness).
    """
    checks: list[Check] = []

    checks.append(Check("non_empty", len(df) > 0, "critical", f"{len(df)} rows"))

    missing = [c for c in required_columns if c not in df.columns]
    checks.append(
        Check("required_columns", not missing, "critical",
              f"missing={missing}" if missing else "all present")
    )

    checks.append(
        Check("min_rows", len(df) >= min_rows, "critical", f"{len(df)} >= {min_rows}")
    )

    for col in non_null_columns or []:
        if col in df.columns:
            nulls = int(df[col].isna().sum())
            checks.append(Check(f"non_null:{col}", nulls == 0, "warn", f"{nulls} nulls"))

    for col in finite_columns or []:
        if col in df.columns:
            series = pd.to_numeric(df[col], errors="coerce").to_numpy(dtype="float64")
            n_bad = int(np.isnan(series).sum() + np.isinf(series).sum())
            checks.append(Check(f"finite:{col}", n_bad == 0, "critical", f"{n_bad} non-finite"))

    if date_column and max_staleness_days is not None and date_column in df.columns and len(df):
        latest = pd.to_datetime(df[date_column]).max().date()
        ref = today or date.today()
        age = (ref - latest).days
        checks.append(
            Check("freshness", age <= max_staleness_days, "warn",
                  f"latest {latest}, {age}d old (limit {max_staleness_days})")
        )

    return ValidationReport(artifact=artifact, checks=checks)


def gate(report: ValidationReport) -> ValidationReport:
    """Raise if the report has any critical failure; otherwise pass it through."""
    if not report.ok:
        names = [c.name for c in report.failures]
        details = "; ".join(f"{c.name}: {c.detail}" for c in report.failures)
        raise DataQualityError(f"{report.artifact} failed critical checks {names} — {details}")
    return report
