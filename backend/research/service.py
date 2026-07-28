"""
The whole pipeline, end to end.

    question
      -> classify, and work out which name it's about
      -> exact lookups for the figures
      -> filtered search for the explanation
      -> build a grounded prompt
      -> generate
      -> check the answer against the evidence
      -> return it with citations and a trace

The trace is returned to the caller on purpose. Being able to see which tools ran
and which chunks came back is what makes a wrong answer diagnosable instead of
mysterious.
"""
from __future__ import annotations

import time

from config import settings

from . import grounding, ingest, llm, orchestrator, prompt
from .types import Chunk

EXAMPLE_QUESTIONS = [
    "Why did the model give NVDA its current signal?",
    "Which features drove the prediction for AMD?",
    "What does 20-day momentum mean and how is it calculated?",
    "How did the model perform after transaction costs?",
    "What does walk-forward validation show?",
    "What are the biggest limitations of this model?",
    "What would make this signal unreliable?",
    "What is the difference between the raw signal and the risk-adjusted position?",
    "Is the model confident or uncertain right now?",
    "Can I trust this model?",
]


def _source_card(ref: dict, chunk_by_id: dict[str, Chunk]) -> dict:
    """One entry for the citations panel in the UI."""
    if ref["kind"] == "structured":
        return {
            "tag": ref["tag"],
            "kind": "structured",
            "artifact_id": f"tool:{ref['tool']}",
            "artifact_type": "structured_lookup",
            "title": ref["tool"],
            "source_path": ref.get("source_path", ""),
            "chunk_id": None,
            "similarity": None,
        }
    chunk = chunk_by_id.get(ref["chunk_id"])
    return {
        "tag": ref["tag"],
        "kind": "retrieved",
        "artifact_id": ref["artifact_id"],
        "artifact_type": ref["artifact_type"],
        "title": chunk.title if chunk else ref["artifact_id"],
        "heading": chunk.heading if chunk else None,
        "source_path": ref["source_path"],
        "chunk_id": ref["chunk_id"],
        "similarity": ref["similarity"],
        "snippet": (chunk.text[:320] + "…") if chunk and len(chunk.text) > 320
                   else (chunk.text if chunk else ""),
    }


def _signal_context(ev: orchestrator.Evidence) -> dict | None:
    sig = ev.tool_result("get_latest_signal")
    if not sig:
        return None
    shap = ev.tool_result("get_top_shap_drivers")
    risk = ev.tool_result("get_risk_summary")
    context = {
        "ticker": sig["ticker"],
        "company": sig.get("company"),
        "sector": sig.get("sector"),
        "signal": sig["signal"],
        "confidence": sig.get("confidence"),
        "chanceLevel": sig.get("chanceLevel", 33.3),
        "expectedReturn5d": sig.get("expectedReturn5d"),
        "risk": sig.get("risk"),
        "model": sig.get("model"),
        "price": sig.get("price"),
        "change": sig.get("change"),
        "generatedAt": sig.get("generatedAt"),
    }
    if shap:
        context["drivers"] = {
            "supporting": shap.get("supporting", [])[:4],
            "opposing": shap.get("opposing", [])[:4],
            "asOf": shap.get("asOf"),
        }
    if risk:
        context["riskControls"] = {
            "level": risk.get("signalRiskLevel"),
            "sizingFactor": risk.get("volatilitySizingFactor"),
            "inProposedBook": risk.get("inProposedBook"),
            "proposedWeight": risk.get("proposedWeight"),
            "limits": risk.get("limits"),
            "note": risk.get("note"),
        }
    return context


def answer(
    question: str,
    ticker: str | None = None,
    model_version: str | None = None,
    run_id: str | None = None,
    top_k: int | None = None,
) -> dict:
    """Answer one research question, grounded in QuantML artifacts."""
    started = time.perf_counter()
    top_k = top_k or settings.research_top_k

    store = ingest.get_index()
    ev = orchestrator.gather(
        question, store, ticker=ticker, model_version=model_version,
        run_id=run_id, top_k=top_k,
    )

    system, user, refs = prompt.build(ev)
    result = llm.generate(ev, system, user, refs)

    structured_blob, evidence_blob = grounding.evidence_blobs(refs, ev)
    warnings = grounding.check(
        result.text, refs, structured_blob, evidence_blob, ev.has_evidence()
    )
    # anything the orchestrator noticed (a false premise, no matches) belongs here too
    warnings = ev.warnings + warnings

    chunk_by_id = {hit.chunk.chunk_id: hit.chunk for hit in ev.chunks}
    elapsed = round((time.perf_counter() - started) * 1000, 1)

    return {
        "question": question,
        "answer": result.text,
        "intent": ev.intent,
        "ticker": ev.ticker,
        "signal_context": _signal_context(ev),
        "sources": [_source_card(r, chunk_by_id) for r in refs],
        "evidence": [
            {
                "chunk_id": hit.chunk.chunk_id,
                "artifact_id": hit.chunk.artifact_id,
                "artifact_type": hit.chunk.artifact_type,
                "title": hit.chunk.title,
                "heading": hit.chunk.heading,
                "source_path": hit.chunk.source_path,
                "similarity": hit.similarity,
                "retrieval_method": hit.retrieval_method,
                "text": hit.chunk.text,
            }
            for hit in ev.chunks
        ],
        "tool_calls": [c.model_dump() for c in ev.tool_calls],
        "retrieval_trace": [s.model_dump() for s in ev.trace],
        "grounding_warnings": warnings,
        "grounded": ev.has_evidence(),
        "llm": {
            "provider": result.provider,
            "model": result.model,
            "note": result.note,
        },
        "latency_ms": elapsed,
        "over_latency_budget": elapsed > settings.research_latency_budget_ms,
    }


def health() -> dict:
    """Whether the index is built and which providers are active."""
    try:
        store = ingest.get_index()
        stats = store.stats()
        ready = stats["chunks"] > 0
    except (OSError, ValueError) as e:
        return {"status": "degraded", "indexReady": False, "error": str(e)}

    provider = (settings.research_llm_provider or "mock").lower()
    return {
        "status": "operational" if ready else "empty",
        "indexReady": ready,
        "index": stats,
        "llm": {
            "provider": provider,
            "mockMode": provider in ("mock", "", "none"),
            "model": settings.research_llm_model or None,
            # never report the key itself, only whether one is present
            "keyConfigured": bool(
                settings.openai_api_key or settings.gemini_api_key
            ),
        },
        "embedding": {
            "provider": settings.research_embedding_provider,
            "active": stats["embedder"],
        },
        "latencyBudgetMs": settings.research_latency_budget_ms,
    }


def artifacts() -> dict:
    """What's currently indexed, for the knowledge-base panel."""
    from . import registry

    found = registry.discover()
    store = ingest.get_index()
    chunk_counts: dict[str, int] = {}
    for chunk in store.chunks:
        chunk_counts[chunk.artifact_id] = chunk_counts.get(chunk.artifact_id, 0) + 1

    return {
        "count": len(found),
        "chunks": len(store.chunks),
        "byType": store.stats()["byType"],
        "artifacts": [
            {
                "artifact_id": a.artifact_id,
                "artifact_type": a.artifact_type,
                "title": a.title,
                "source_path": a.source_path,
                "ticker": a.ticker,
                "model_version": a.model_version,
                "date_range": a.date_range,
                "created_at": a.created_at,
                "chunks": chunk_counts.get(a.artifact_id, 0),
            }
            for a in found
        ],
    }
