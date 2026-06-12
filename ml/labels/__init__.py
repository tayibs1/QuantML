"""
Label definitions - the Y of the problem, kept as real artifacts.

The thing I wanted to avoid (AFML makes a big deal of this): the label being an
afterthought stuffed inside the training loop. So it's an explicit object with
its event timing (T) and a sample weight (W) that accounts for the overlapping,
non-IID nature of price data. Writing it out as labels.parquet / events.parquet
means I can audit it, swap schemes, and compare them without touching model code.

Two schemes:

  - outperformance  the production label: cross-sectional terciles of the h-day
    forward return (AVOID / HOLD / BUY). This is what training uses.
  - triple_barrier  a research alternative (vol-scaled profit-take / stop-loss /
    time barriers). Scaffolded, not wired in yet.
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
