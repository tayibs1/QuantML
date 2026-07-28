"""
Turning gathered evidence into a prompt.

The rules here do the real work of keeping answers honest. A language model asked
about a stock will happily produce a confident, fluent, completely invented
answer, because it has read a great deal about markets and none of it is about
this model. The prompt's job is to make that behaviour harder than the correct
one.

Three things carry most of the weight:

  the exact figures arrive pre-computed, so there is nothing to calculate and
  therefore nothing to get wrong

  every piece of evidence carries a citation tag, and the answer has to use them,
  which makes an unsupported sentence visibly unsupported

  the model is told to say what is missing, because "the pipeline hasn't produced
  that yet" is a genuinely good answer and models will invent something rather
  than give it unless asked
"""
from __future__ import annotations

import json

from .orchestrator import Evidence

DISCLAIMER = (
    "This is a model-generated research explanation, not investment advice."
)

SYSTEM_PROMPT = f"""You are QuantML Research AI.

You explain what QuantML's machine learning model produced and why, using only
the evidence supplied with each question. QuantML ranks stocks; you explain those
rankings. You do not advise anyone on what to do with them.

GROUNDING RULES

1. Use only the STRUCTURED DATA and RETRIEVED EVIDENCE blocks provided. Your own
   knowledge of markets, companies or finance is not evidence and must not appear
   as fact in the answer.
2. Every number you state must appear in the evidence. Never calculate a new
   figure, never estimate one, never round a missing one into existence.
3. Cite the evidence for each substantive claim using its tag, like [S1] or [E3].
   A claim with no tag reads as unsupported.
4. If the evidence does not answer part of the question, say so plainly and name
   what is missing. This is a correct answer, not a failure.
5. If the question assumes something the evidence contradicts, correct it first
   and answer the corrected question.

WHAT THE OUTPUT MEANS

BUY, HOLD and AVOID are relative rankings within the scored universe on a 5-day
horizon, produced by cutting predicted returns into thirds. A BUY means the model
ranks the name in the top third right now. It is not a forecast that the price
will rise, and not a judgement about the company.

Confidence is a probability across three classes, so roughly 33% is the level
that means no opinion. Read confidence against 33, not against zero.

Keep these separate and never let one stand in for another:
  what the model output
  which features moved that output
  what validation and backtests showed
  what the risk layer did with it
  what the system cannot see
  your own summary

WHAT YOU MUST NOT DO

Do not tell anyone to buy, sell, hold or size a position.
Do not predict prices or returns beyond quoting the model's own figure.
Do not describe anything as guaranteed, safe, certain or low-risk.
Do not assess whether a company is good, cheap or well run — the model reads only
price and volume and has no view on any of that.

ANSWER FORMAT

Use these sections, omitting any with no evidence behind it:

**Short answer** — two or three sentences.
**Model signal** — the exact output, with confidence read against the 33% floor.
**Main drivers** — which features pushed which way, and what they mean.
**Evidence** — validation and backtest results that bear on it.
**Risks and limitations** — what weakens this, and what the model cannot see.
**What could make this wrong** — the specific conditions that would break it.
**Sources** — the tags you used.

End with exactly this line:
{DISCLAIMER}
"""


def _format_structured(ev: Evidence) -> tuple[str, list[dict]]:
    """Lay out the exact figures with citation tags."""
    blocks, refs = [], []
    for i, call in enumerate((c for c in ev.tool_calls if c.ok), start=1):
        tag = f"S{i}"
        blocks.append(
            f"[{tag}] {call.tool}({json.dumps(call.arguments)})\n"
            f"{json.dumps(call.result, indent=2, default=str)}"
        )
        refs.append({
            "tag": tag,
            "kind": "structured",
            "tool": call.tool,
            "source_path": (call.result or {}).get("source_path", ""),
        })

    failed = [c for c in ev.tool_calls if not c.ok]
    if failed:
        blocks.append(
            "UNAVAILABLE (say so if the question needs it):\n"
            + "\n".join(f"  {c.tool}: {c.note}" for c in failed)
        )
    return "\n\n".join(blocks) if blocks else "(none)", refs


def _format_evidence(ev: Evidence) -> tuple[str, list[dict]]:
    """Lay out the retrieved passages with citation tags."""
    blocks, refs = [], []
    for i, hit in enumerate(ev.chunks, start=1):
        tag = f"E{i}"
        c = hit.chunk
        header = f"[{tag}] {c.title}"
        if c.heading:
            header += f" — {c.heading}"
        header += f" ({c.artifact_type}, {c.source_path}, chunk {c.chunk_id})"
        blocks.append(f"{header}\n{c.text}")
        refs.append({
            "tag": tag,
            "kind": "retrieved",
            "artifact_id": c.artifact_id,
            "artifact_type": c.artifact_type,
            "chunk_id": c.chunk_id,
            "source_path": c.source_path,
            "similarity": hit.similarity,
        })
    return "\n\n".join(blocks) if blocks else "(none)", refs


def build(ev: Evidence) -> tuple[str, str, list[dict]]:
    """Return (system_prompt, user_prompt, citation_refs)."""
    structured, s_refs = _format_structured(ev)
    retrieved, e_refs = _format_evidence(ev)

    parts = [f"QUESTION\n{ev.question}"]

    if ev.ticker:
        parts.append(f"SUBJECT\nTicker: {ev.ticker}")

    if ev.warnings:
        parts.append(
            "CORRECTIONS — address these before anything else:\n"
            + "\n".join(f"  - {w}" for w in ev.warnings)
        )

    if ev.intent == "advice_request":
        parts.append(
            "NOTE\nThis asks what to do rather than what the model produced. "
            "Decline the decision, explain what the model output actually says, "
            "and leave the choice with the reader."
        )
    elif ev.intent == "certainty_request":
        parts.append(
            "NOTE\nThis asks for a guarantee or an exact future figure. Neither "
            "exists. Explain what the model does produce, what its measured "
            "accuracy is, and why certainty is not available."
        )

    parts.append(f"STRUCTURED DATA — exact figures, use these verbatim\n{structured}")
    parts.append(f"RETRIEVED EVIDENCE — explanatory material\n{retrieved}")
    parts.append(
        "Answer using the required format. Cite tags. State what is missing "
        "rather than filling it in."
    )

    return SYSTEM_PROMPT, "\n\n".join(parts), s_refs + e_refs
