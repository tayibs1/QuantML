"""
Producing the final answer.

Three providers behind one call. The default is `mock`, which writes the answer
directly from the evidence with no model involved at all.

Mock mode is not a placeholder. Because every figure comes from the structured
lookups and every citation comes from the retrieval, an answer assembled by code
is exactly as accurate as one written by a language model — and it cannot
hallucinate, cannot cost anything, and cannot fail. What it lacks is fluency and
the ability to handle a question the templates didn't anticipate.

That makes it the right default for a demo and for CI, and the right thing to
compare a real model against.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from config import settings

from .orchestrator import Evidence
from .prompt import DISCLAIMER


class LLMResult:
    def __init__(self, text: str, provider: str, model: str = "", note: str = ""):
        self.text = text
        self.provider = provider
        self.model = model
        self.note = note


# --- mock -------------------------------------------------------------------

def _pct(value, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}%"
    except (TypeError, ValueError):
        return "unknown"


def _rate(value, digits: int = 1) -> str:
    """Show a stored fraction as a percentage. 0.0883 reads as 8.8%."""
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "unknown"


def _confidence_reading(confidence) -> str:
    """Put a confidence number in context against the 33% guessing floor."""
    try:
        c = float(confidence)
    except (TypeError, ValueError):
        return ""
    if c < 40:
        return ("barely above the 33% level that means no opinion, so this is a "
                "weak call")
    if c < 55:
        return "a modest lead over the 33% no-opinion level"
    if c < 70:
        return "a reasonably firm call by this model's standards"
    return "a strong call by this model's standards"


def _mock_signal_section(ev: Evidence) -> list[str]:
    sig = ev.tool_result("get_latest_signal")
    if not sig:
        return []
    reading = _confidence_reading(sig.get("confidence"))
    return [
        "**Model signal**",
        f"{sig['ticker']} ({sig.get('company')}) is currently **{sig['signal']}** at "
        f"{_pct(sig.get('confidence'))} confidence — {reading} [S1]. "
        f"Expected 5-day return {_pct(sig.get('expectedReturn5d'), 2)}, "
        f"risk level {sig.get('risk')}, model {sig.get('model')}, "
        f"generated {(sig.get('generatedAt') or '')[:10]}.",
        f"{sig['signal']} is a relative ranking within the {sig.get('sector', '')} "
        f"universe scored that day, not a forecast that the price will move.",
    ]


def _mock_drivers_section(ev: Evidence) -> list[str]:
    shap = ev.tool_result("get_top_shap_drivers")
    if not shap:
        return []
    lines = ["**Main drivers**"]
    support = shap.get("supporting", [])[:3]
    oppose = shap.get("opposing", [])[:3]
    if support:
        lines.append("Pushed the prediction towards this label — *supports*:")
        lines += [
            f"  - {d['label']} ({d['key']}) supports, contribution "
            f"{d['contribution']:+.4f}, feature value {d['featureValue']}"
            for d in support
        ]
    if oppose:
        lines.append("Pushed the prediction against it — *opposes*:")
        lines += [
            f"  - {d['label']} ({d['key']}) opposes, contribution "
            f"{d['contribution']:+.4f}, feature value {d['featureValue']}"
            for d in oppose
        ]
        lines.append(
            "The opposing drivers matter: the model reached its label despite them, "
            "which makes the call less clear-cut than the headline suggests."
        )
    lines.append(
        "Contributions are in the model's internal scoring units, so only their "
        "relative sizes mean anything."
    )
    return lines


def _mock_evidence_section(ev: Evidence) -> list[str]:
    lines = []
    metrics = ev.tool_result("get_model_metrics")
    backtest = ev.tool_result("get_backtest_summary")
    if metrics:
        acc = metrics.get("accuracy")
        acc_pct = acc * 100 if isinstance(acc, int | float) and acc <= 1 else acc
        lines.append(
            f"Validated by {metrics.get('validation', 'walk-forward')} on "
            f"{metrics.get('trainingWindow', 'the training window')}. Every figure "
            f"here is out-of-sample: each fold was tested only on dates after the "
            f"data it trained on. AUC {metrics.get('auc')} against 0.50 for chance, "
            f"accuracy {_pct(acc_pct)} against 33% for chance. The edge is real but "
            f"small."
        )
    if backtest:
        m = backtest.get("metrics", {})
        costs = backtest.get("costsBps", {})
        lines.append(
            f"Backtest over {backtest.get('window', {}).get('start')} to "
            f"{backtest.get('window', {}).get('end')}, net of "
            f"{costs.get('roundTrip')} bps round-trip costs: Sharpe {m.get('sharpe')}, "
            f"CAGR {_rate(m.get('cagr'))}, max drawdown {_rate(m.get('maxDrawdown'))}. "
            f"Buy-and-hold QQQ returned {_rate(m.get('benchTotalReturn'))} against the "
            f"strategy's {_rate(m.get('totalReturn'))} over the same window, so the "
            f"model underperformed simply holding the index."
        )
        tt = backtest.get("tickerTrades")
        count = (tt or {}).get("count") or 0
        if count:
            lines.append(
                f"This name has {count} closed trade{'s' if count != 1 else ''} in "
                f"the ledger, win rate {tt['winRate']}%, average return "
                f"{tt['avgReturn']}%. "
                + ("That is far too small a sample to conclude anything from."
                   if count < 30 else
                   "Still a modest sample for a claim about skill.")
            )
    return ["**Evidence**", *lines] if lines else []


def _mock_risk_section(ev: Evidence) -> list[str]:
    lines = []
    risk = ev.tool_result("get_risk_summary")
    if risk:
        lines.append(
            f"Risk level {risk['signalRiskLevel']} means volatility rank only — it "
            f"excludes earnings dates, company news, liquidity and crowding. "
            f"Sizing factor {risk['volatilitySizingFactor']}."
        )
        if risk.get("inProposedBook"):
            lines.append(
                f"The risk layer proposes a {_pct(risk.get('proposedWeight', 0) * 100)} "
                f"position, under a {_pct(risk['limits']['maxNameWeight'] * 100)} "
                f"per-name cap and a {_pct(risk['limits']['maxSectorWeight'] * 100)} "
                f"sector cap."
            )
        elif risk.get("note"):
            lines.append(risk["note"])
    lines.append(
        "The model reads only price and volume. It has no access to fundamentals, "
        "earnings, guidance, filings or news, so anything driven by those is "
        "invisible to it until the price reacts."
    )
    return ["**Risks and limitations**", *lines]


def _mock_wrong_section(ev: Evidence) -> list[str]:
    reasons = []
    sig = ev.tool_result("get_latest_signal")
    if sig:
        try:
            if float(sig.get("confidence", 0)) < 45:
                reasons.append(
                    f"Confidence is {_pct(sig.get('confidence'))}, close to the 33% "
                    f"no-opinion floor. The model is not expressing much of a view."
                )
        except (TypeError, ValueError):
            pass
        if sig.get("risk") in ("High", "Elevated"):
            reasons.append(
                f"{sig['risk']} volatility means a wider range of outcomes around "
                f"whatever the model expects."
            )
    shap = ev.tool_result("get_top_shap_drivers")
    if shap and shap.get("opposing"):
        reasons.append(
            "Several features push against the chosen label, so a small change in "
            "the data could flip it."
        )
    if shap and shap.get("supporting"):
        momentum = [d for d in shap["supporting"] if d["key"].startswith("ret_")
                    or d["key"] == "rel_strength_20"]
        if len(momentum) >= 2:
            reasons.append(
                "The supporting drivers are mostly momentum features, which overlap. "
                "That is one bet expressed several ways, not independent confirmation."
            )
    reasons.append(
        "A regime change would break the historical relationships the model learned. "
        "Momentum signals tend to fail hardest at turning points."
    )
    reasons.append(
        "An upcoming earnings release or company announcement would dominate the "
        "5-day horizon, and the model has no knowledge of the schedule."
    )
    return ["**What could make this wrong**", *[f"  - {r}" for r in reasons]]


def _mock_sources_section(refs: list[dict]) -> list[str]:
    if not refs:
        return []
    lines = ["**Sources**"]
    for r in refs[:12]:
        if r["kind"] == "structured":
            lines.append(f"  [{r['tag']}] {r['tool']} — {r.get('source_path', '')}")
        else:
            lines.append(
                f"  [{r['tag']}] {r['artifact_type']} — {r['source_path']} "
                f"(chunk {r['chunk_id']}, similarity {r['similarity']})"
            )
    return lines


def mock_answer(ev: Evidence, refs: list[dict]) -> str:
    """Write the answer straight from the evidence, no model involved."""
    parts: list[list[str]] = []

    if not ev.has_evidence():
        return (
            "**Short answer**\n"
            "I can't answer that from QuantML's artifacts. Nothing in the index "
            "matches this question.\n\n"
            "I can only answer from what QuantML itself has produced: current "
            "signals, feature attribution, validation and backtest reports, the "
            "risk framework and the project documentation. I don't have company "
            "fundamentals, news or filings.\n\n"
            f"{DISCLAIMER}"
        )

    # --- opening ---
    if ev.intent == "advice_request":
        parts.append([
            "**Short answer**",
            "I can't tell you what to do with this, and QuantML isn't built to. "
            "What I can do is lay out what the model produced and how much weight "
            "the evidence supports putting on it.",
        ])
    elif ev.intent == "certainty_request":
        metrics = ev.tool_result("get_model_metrics")
        auc = metrics.get("auc") if metrics else None
        parts.append([
            "**Short answer**",
            "There's no certainty available here, and nothing in QuantML can "
            "provide one. The model estimates a probability across three relative "
            "rankings on a 5-day horizon"
            + (f", and its measured out-of-sample AUC is {auc} against 0.50 for "
               f"chance [S1]" if auc else "")
            + ". That is a small edge, not a forecast, and it is wrong often.",
        ])
    elif ev.warnings and ev.signal_context:
        parts.append([
            "**Short answer**",
            ev.warnings[0] + " The explanation below covers the signal the model "
            "actually issued.",
        ])
    else:
        sig = ev.tool_result("get_latest_signal")
        feature = ev.tool_result("get_feature_definition")
        if feature:
            first = feature["definition"].split("\n\n")[0].strip()
            parts.append([
                "**Short answer**",
                f"**{feature['key']}** is {feature['label'].lower()}. {first} [S1]",
            ])
        elif sig:
            parts.append([
                "**Short answer**",
                f"{sig['ticker']} is currently a **{sig['signal']}** at "
                f"{_pct(sig.get('confidence'))} confidence [S1]. The sections below "
                f"cover what drove that, what the validation evidence supports, and "
                f"what would undermine it.",
            ])
        else:
            parts.append([
                "**Short answer**",
                "Answering from QuantML's indexed artifacts. The evidence used is "
                "cited below.",
            ])

    feature = ev.tool_result("get_feature_definition")
    if feature:
        parts.append([
            "**Definition**",
            feature["definition"],
            feature["note"],
        ])

    for section in (
        _mock_signal_section(ev),
        _mock_drivers_section(ev),
        _mock_evidence_section(ev),
        _mock_risk_section(ev),
        _mock_wrong_section(ev),
        _mock_sources_section(refs),
    ):
        if section:
            parts.append(section)

    if ev.warnings:
        parts.append(["**Notes on evidence**", *[f"  - {w}" for w in ev.warnings]])

    body = "\n\n".join("\n".join(block) for block in parts)
    return f"{body}\n\n{DISCLAIMER}"


# --- real providers -----------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _openai_answer(system: str, user: str) -> LLMResult:
    key = settings.openai_api_key or os.environ.get("OPENAI_API_KEY", "")
    if not key:
        raise RuntimeError("no OpenAI key configured")
    model = settings.research_llm_model or "gpt-4o-mini"
    data = _post_json(
        f"{settings.research_llm_base_url.rstrip('/')}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        },
        {"Authorization": f"Bearer {key}"},
        settings.research_llm_timeout,
    )
    return LLMResult(data["choices"][0]["message"]["content"], "openai", model)


def _gemini_answer(system: str, user: str) -> LLMResult:
    key = settings.gemini_api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        raise RuntimeError("no Gemini key configured")
    model = settings.research_llm_model or "gemini-2.0-flash"
    data = _post_json(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2000},
        },
        {"x-goog-api-key": key},
        settings.research_llm_timeout,
    )
    return LLMResult(
        data["candidates"][0]["content"]["parts"][0]["text"], "gemini", model
    )


def generate(ev: Evidence, system: str, user: str, refs: list[dict]) -> LLMResult:
    """Answer the question, falling back to mock if the provider fails.

    Falling back rather than erroring is deliberate: a rate limit or a dropped
    connection should cost fluency, not the answer.
    """
    provider = (settings.research_llm_provider or "mock").lower()
    if provider in ("mock", "", "none"):
        return LLMResult(mock_answer(ev, refs), "mock")

    try:
        if provider == "openai":
            return _openai_answer(system, user)
        if provider == "gemini":
            return _gemini_answer(system, user)
        return LLMResult(mock_answer(ev, refs), "mock", note=f"unknown provider {provider}")
    except (urllib.error.URLError, RuntimeError, KeyError, ValueError, TimeoutError) as e:
        return LLMResult(
            mock_answer(ev, refs), "mock",
            note=f"{provider} unavailable ({type(e).__name__}), used mock instead",
        )
