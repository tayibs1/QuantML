"""
Label definitions — the **Y** of the learning problem, as first-class artifacts.

A core principle (López de Prado, *Advances in Financial ML*): a label is not an
afterthought buried in the training loop. It is an explicit, documented object
defined alongside its event timing (T) and a sample weight (W) that accounts for
the non-IID, overlapping nature of financial observations. Making the label a
versioned artifact (`labels.parquet`, `events.parquet`) lets you audit, swap and
compare labelling schemes without touching the model code.

Two schemes live here:

  - `outperformance`  — the production label: cross-sectional terciles of the
    h-day forward return (AVOID / HOLD / BUY). In use by the training pipeline.
  - `triple_barrier`  — a research-grade alternative (profit-take / stop-loss /
    time barriers, volatility-scaled). Scaffolded, not yet wired in.
"""
from __future__ import annotations

from .outperformance import (
    AVOID,
    BUY,
    CLASS_TO_SIGNAL,
    HOLD,
    LABEL_HORIZON,
    build_label_artifacts,
    make_labels,
)

__all__ = [
    "AVOID",
    "HOLD",
    "BUY",
    "CLASS_TO_SIGNAL",
    "LABEL_HORIZON",
    "make_labels",
    "build_label_artifacts",
]
