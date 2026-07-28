"""
Checking the answer against the evidence it was supposed to use.

The prompt tells the model not to invent figures. This checks whether it obeyed.
It runs after generation and reports what it finds rather than blocking, because
a warning the reader can see beats a silent rewrite.

What it looks for:

  numbers that appear in the answer but nowhere in the evidence
  citation tags pointing at evidence that was never supplied
  no citations at all
  the disclaimer going missing
  advice language, which this assistant must never produce

The number check is deliberately forgiving. A model that writes "roughly 9%" when
the evidence says 0.0883 is rephrasing, not inventing, and flagging it as a
hallucination would train the reader to ignore the warnings. So percentages are
matched against their decimal forms, and a small tolerance is allowed.
"""
from __future__ import annotations

import json
import re

from .prompt import DISCLAIMER

NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
TAG = re.compile(r"\[([SE]\d+)\]")

# Years, small counts and round numbers appear in ordinary prose and aren't claims.
IGNORED_NUMBERS = {0.0, 1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 100.0, 33.0, 33.3, 50.0}

ADVICE_PHRASES = [
    r"\byou should (buy|sell|hold|invest|short|avoid buying)\b",
    r"\bi recommend (buying|selling|investing|shorting)\b",
    r"\bworth buying\b", r"\bgood investment\b", r"\bstrong buy\b",
    r"\bguaranteed?\b", r"\brisk[- ]free\b", r"\bcan'?t lose\b",
    r"\bwill definitely\b", r"\bsure to (rise|gain|profit)\b",
]


def _evidence_numbers(structured_blob: str, evidence_blob: str) -> set[float]:
    """Every number the answer is allowed to use, plus useful restatements."""
    allowed: set[float] = set()
    for blob in (structured_blob, evidence_blob):
        for raw in NUMBER.findall(blob):
            try:
                value = float(raw)
            except ValueError:
                continue
            allowed.add(value)
            allowed.add(round(value, 2))
            # a rate stored as 0.0883 is fairly quoted as 8.83% or 8.8%
            allowed.add(round(value * 100, 2))
            allowed.add(round(value * 100, 1))
            allowed.add(round(value * 100))
            allowed.add(round(value / 100, 4))
            allowed.add(abs(value))
            allowed.add(round(abs(value * 100), 1))
    return allowed


def _strip_non_claims(answer: str) -> str:
    """Remove the digits that are part of a name rather than a claim.

    Plenty of things in these answers contain digits without asserting anything:
    feature keys like rsi_14, chunk ids like corpus:model_card#3, dates, and the
    citation tags themselves. Counting those as invented figures would fill the
    warnings with noise and train the reader to ignore them.
    """
    text = answer
    # the sources list is all identifiers, no claims
    text = re.split(r"\*\*Sources\*\*", text)[0]
    text = TAG.sub(" ", text)
    text = re.sub(r"\d{4}-\d{2}-\d{2}", " ", text)            # dates
    text = re.sub(r"[a-z]+(?:_[a-z0-9]+)+", " ", text)        # feature keys
    text = re.sub(r"\S+#\d+", " ", text)                      # chunk ids
    text = re.sub(r"\b\d+-fold\b", " ", text)                 # "6-fold"
    text = re.sub(r"\(\s*\d+\s*\)", " ", text)                # "RSI (14)"
    return text


def _close_to_allowed(value: float, allowed: set[float]) -> bool:
    if value in allowed or round(value, 1) in allowed or round(value) in allowed:
        return True
    # within half a percent of something in the evidence counts as a restatement
    return any(abs(value - a) <= max(0.05, abs(a) * 0.005) for a in allowed)


def check(answer: str, refs: list[dict], structured_blob: str,
          evidence_blob: str, has_evidence: bool) -> list[str]:
    """Return a list of human-readable warnings. Empty means it looks clean."""
    warnings: list[str] = []

    # --- citations ---
    used = set(TAG.findall(answer))
    known = {r["tag"] for r in refs}
    if refs and not used:
        warnings.append(
            "The answer cites no sources, so its claims cannot be traced back to "
            "a QuantML artifact."
        )
    unknown = used - known
    if unknown:
        warnings.append(
            f"The answer cites {', '.join(sorted(unknown))}, which was not among "
            f"the evidence provided."
        )

    # --- disclaimer ---
    if DISCLAIMER.lower() not in answer.lower():
        warnings.append("The required 'not investment advice' disclaimer is missing.")

    # --- advice language ---
    lowered = answer.lower()
    for pattern in ADVICE_PHRASES:
        if re.search(pattern, lowered):
            warnings.append(
                f"The answer contains language that reads as advice or a guarantee "
                f"(matched {pattern!r}). This assistant explains model output only."
            )
            break

    # --- unsupported numbers ---
    if has_evidence:
        allowed = _evidence_numbers(structured_blob, evidence_blob)
        stripped = _strip_non_claims(answer)
        unsupported = []
        for raw in NUMBER.findall(stripped):
            try:
                value = float(raw)
            except ValueError:
                continue
            if abs(value) in IGNORED_NUMBERS or value in IGNORED_NUMBERS:
                continue
            if 1900 <= value <= 2100 and value == int(value):
                continue  # a year
            if not _close_to_allowed(value, allowed):
                unsupported.append(raw)
        if unsupported:
            shown = ", ".join(sorted(set(unsupported))[:6])
            warnings.append(
                f"These figures appear in the answer but not in the retrieved "
                f"evidence: {shown}. Treat them as unverified."
            )

    if not has_evidence and "can't answer" not in lowered and "cannot answer" not in lowered:
        warnings.append(
            "No supporting artifacts were retrieved, so this answer is not grounded "
            "in QuantML evidence."
        )

    return warnings


def evidence_blobs(refs: list[dict], ev) -> tuple[str, str]:
    """Rebuild the text the answer was allowed to draw numbers from."""
    structured = json.dumps(
        [c.result for c in ev.tool_calls if c.ok], default=str
    )
    retrieved = "\n".join(hit.chunk.text for hit in ev.chunks)
    return structured, retrieved
