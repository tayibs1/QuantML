"""
Deciding what evidence a question needs.

A question about a specific stock needs that stock's exact numbers plus material
explaining what they mean. A question about whether the model can be trusted
needs validation and limitations and nothing ticker-specific. Retrieving the same
way for both wastes the prompt on irrelevant text and buries the useful part.

So the question is classified first, and the classification picks which exact
lookups to run and which kinds of document to search. Classification is keyword
based rather than model based: it is inspectable, instant, free, and when it is
wrong the fallback is a broad search rather than a bad answer.

Two checks here matter more than the routing.

The first catches questions built on a false premise. Someone asking why NVDA got
a BUY when the model actually says HOLD must be corrected, not answered — an
assistant that explains the reasoning behind a signal that was never issued is
the worst possible failure for this system.

The second catches questions no model output can answer: guarantees, exact future
prices, and requests for advice on what to do.
"""
from __future__ import annotations

import re

from . import tools
from .embeddings import get_embedder
from .types import RetrievalStep, ToolCall
from .vectorstore import VectorStore

# Anything the model literally cannot know. These get an answer about uncertainty
# instead of an attempt at the question.
CERTAINTY_PATTERNS = [
    r"\bguarantee\w*\b", r"\bcertain(ly)?\b", r"\bsure thing\b", r"\brisk[- ]free\b",
    r"\bexact(ly)? (future|price|return|profit)\b", r"\bhow much (will|would) .* (make|earn|profit)\b",
    r"\bwill .* (go up|go down|rise|fall|crash|moon)\b",
    r"\bprice target\b", r"\bnext week'?s? (return|price)\b",
]

# Requests for a decision rather than an explanation.
ADVICE_PATTERNS = [
    r"\bshould i (buy|sell|hold|invest|short|dump)\b",
    r"\b(is|are) (it|this|that|they) a (good|bad) (buy|investment|stock)\b",
    r"\bwhat should i (do|buy|sell|invest)\b",
    r"\bhow much should i (buy|invest|put)\b",
    r"\btell me what to (buy|do)\b",
]

# intent -> (patterns, artifact types worth searching)
INTENTS: dict[str, tuple[list[str], list[str]]] = {
    "feature_definition": (
        [r"\bwhat (does|is) .*\bmean\b", r"\bhow is .* (calculated|computed|worked out)\b",
         r"\bdefine\b", r"\bwhat is (the )?(momentum|rsi|macd|atr|volatility|bollinger|obv|skew|kurtosis)\b",
         r"\bfeature\b.*\b(mean|definition|explain)\b"],
        ["feature_dictionary", "model_card"],
    ),
    "trust_limitations": (
        [r"\b(can|should) i trust\b", r"\blimitation", r"\bweakness", r"\bhow reliable\b",
         r"\bdistrust\b", r"\bwhat.*wrong\b", r"\bunreliable\b", r"\bfail\b",
         r"\bhow good is\b", r"\boverfit"],
        ["model_card", "validation_report", "calibration_report", "drift_report",
         "walk_forward_report", "backtest_report"],
    ),
    "validation": (
        [r"\bwalk[- ]forward\b", r"\bvalidat", r"\bcross[- ]validat", r"\bout[- ]of[- ]sample\b",
         r"\bmethodolog", r"\bhow (was|is) .*(tested|trained|evaluated)\b", r"\bleakage\b",
         r"\bauc\b", r"\baccuracy\b", r"\bcalibrat"],
        ["validation_report", "walk_forward_report", "model_card",
         "calibration_report", "model_registry_entry"],
    ),
    "backtest_costs": (
        [r"\bbacktest", r"\bcost", r"\bslippage\b", r"\bcommission\b", r"\bfees\b",
         r"\bsharpe\b", r"\bdrawdown\b", r"\bcagr\b", r"\breturn(s)? (after|net)\b",
         r"\bperform", r"\bbenchmark\b", r"\bhistorical", r"\bworked historically\b"],
        ["backtest_report", "validation_report", "model_card"],
    ),
    "risk": (
        [r"\brisk", r"\bexposure\b", r"\bposition siz", r"\bconcentrat",
         r"\bcap\b", r"\bvolatilit", r"\bhow much.*hold\b", r"\brisk[- ]adjusted\b"],
        ["risk_report", "latest_signal", "model_card"],
    ),
    "signal_explanation": (
        [r"\bwhy\b", r"\b(what|which) (features?|factors?)?\s*(drove|pushed|caused|moved)\b",
         r"\bdriver", r"\bshap\b", r"\battribution\b",
         r"\bexplain (the |this )?signal\b", r"\bsignal for\b",
         r"\bpushed? (it |the prediction )?(up|down|towards|against)\b",
         r"\bwhich features\b"],
        ["latest_signal", "shap_summary", "feature_dictionary", "model_card"],
    ),
    "coverage": (
        [r"\bwhat (artifacts|data|sources|documents)\b", r"\bwhat can you\b",
         r"\bhow many (signals|names|stocks)\b", r"\bwhat do you know\b"],
        ["documentation", "signal_history"],
    ),
}

TICKER = re.compile(r"\b[A-Z]{1,5}\b")

# Vocabulary that means a question is about this system. Used to spot questions
# that are simply off-topic.
#
# A similarity threshold would be the obvious way to do this and it does not work:
# the default embedder scores "write me a poem" higher against this corpus than it
# scores a genuine question about trading costs, because it matches on shared
# vocabulary rather than meaning. Checking for domain words is cruder but it
# actually separates the two.
DOMAIN_TERMS = frozenset("""
signal signals model models prediction predictions predicted feature features
driver drivers shap attribution confidence backtest backtests validation validate
walk forward oos sample sharpe sortino drawdown cagr auc accuracy calibration
calibrated drift regime volatility momentum risk exposure position sizing weight
cap caps portfolio universe ticker stock stocks buy hold avoid quantml xgboost
return returns performance cost costs commission slippage bps benchmark qqq
trade trades rebalance equity limitation limitations trust reliable overfit
leakage tercile ranking rank probability price volume rsi macd atr bollinger
obv skew kurtosis sma ema pipeline artifact artifacts index retrieval training
trained horizon label labels class classes
""".split())


def in_scope(question: str, intent: str, ticker: str | None) -> bool:
    """Is this question about QuantML at all?

    Anything that matched an intent, or names a stock in the universe, is on
    topic. Otherwise the question has to use at least one word from the domain.
    """
    if ticker or intent != "general":
        return True
    from .embeddings import tokenize

    return any(t in DOMAIN_TERMS for t in tokenize(question))

# Words shaped like tickers that never are one in a sentence.
NOT_TICKERS = {
    "AI", "ML", "API", "BUY", "HOLD", "SHAP", "AUC", "CAGR", "OK", "I", "A",
    "THE", "IS", "IT", "US", "UK", "CEO", "ETF", "IPO", "PE", "EPS", "RSI",
    "MACD", "ATR", "OBV", "NAV", "QQQ", "AND", "OR", "WHY", "HOW", "WHAT",
    "DO", "MY", "IN", "ON", "TO", "OF", "FOR", "VS", "P", "L",
}


def _universe() -> dict[str, str]:
    """ticker -> company name for everything currently scored."""
    from config import settings

    payload = tools._read_json(settings.signals_dir / "latest.json")
    if not payload:
        return {}
    return {s["ticker"]: s.get("company", s["ticker"]) for s in payload.get("signals", [])}


def resolve_ticker(question: str, explicit: str | None = None) -> str | None:
    """Work out which name the question is about, if any."""
    universe = _universe()
    if explicit and explicit.upper() in universe:
        return explicit.upper()
    if explicit:
        return explicit.upper()  # keep it so the tool can report it as unknown

    for candidate in TICKER.findall(question):
        if candidate not in NOT_TICKERS and candidate in universe:
            return candidate

    lowered = question.lower()
    for ticker, company in universe.items():
        first = company.lower().split()[0]
        if len(first) >= 4 and first in lowered:
            return ticker
    return None


def classify(question: str) -> tuple[str, list[str]]:
    """Work out what kind of question this is and which artifact types suit it."""
    q = question.lower()

    if any(re.search(p, q) for p in ADVICE_PATTERNS):
        return "advice_request", ["model_card", "risk_report", "documentation"]
    if any(re.search(p, q) for p in CERTAINTY_PATTERNS):
        return "certainty_request", ["model_card", "validation_report", "backtest_report"]

    # score every intent, take the strongest; ties go to the earlier definition
    best, best_hits = "general", 0
    for intent, (patterns, _) in INTENTS.items():
        hits = sum(1 for p in patterns if re.search(p, q))
        if hits > best_hits:
            best, best_hits = intent, hits

    if best == "general":
        return "general", []
    return best, INTENTS[best][1]


def _claimed_signal(question: str) -> str | None:
    """Spot a question that asserts what the signal is, so it can be checked."""
    q = question.lower()
    for label in ("buy", "avoid", "hold"):
        if re.search(rf"\b{label}\b.*\bsignal\b|\bsignal\b.*\b{label}\b|"
                     rf"\b(gave|give|issued|generated|flagged|rated)\b.*\b{label}\b", q):
            return label.upper()
    return None


class Evidence:
    """Everything gathered for one question, ready to become a prompt."""

    def __init__(self, question: str, intent: str, ticker: str | None):
        self.question = question
        self.intent = intent
        self.ticker = ticker
        self.tool_calls: list[ToolCall] = []
        self.chunks: list = []
        self.trace: list[RetrievalStep] = []
        self.warnings: list[str] = []
        self.signal_context: dict | None = None
        self.out_of_scope = False

    def call(self, name: str, **kwargs) -> dict:
        fn = tools.TOOLS[name]
        result = fn(**kwargs)
        ok = bool(result.get("ok"))
        self.tool_calls.append(
            ToolCall(
                tool=name,
                arguments=kwargs,
                ok=ok,
                result=result if ok else None,
                note=None if ok else result.get("reason"),
            )
        )
        self.trace.append(
            RetrievalStep(
                step=f"tool:{name}",
                detail=f"{name}({', '.join(f'{k}={v!r}' for k, v in kwargs.items())}) "
                       f"-> {'ok' if ok else result.get('reason', 'no data')}",
                result_count=1 if ok else 0,
            )
        )
        return result

    def tool_result(self, name: str) -> dict | None:
        for call in self.tool_calls:
            if call.tool == name and call.ok:
                return call.result
        return None

    def has_evidence(self) -> bool:
        if self.out_of_scope:
            return False
        return bool(self.chunks) or any(c.ok for c in self.tool_calls)


def gather(
    question: str,
    store: VectorStore,
    ticker: str | None = None,
    model_version: str | None = None,
    run_id: str | None = None,
    top_k: int = 6,
) -> Evidence:
    """Run the retrieval plan for this question and return everything found."""
    intent, artifact_types = classify(question)
    resolved = resolve_ticker(question, ticker)
    ev = Evidence(question, intent, resolved)
    ev.trace.append(
        RetrievalStep(
            step="classify",
            detail=f"intent={intent}"
                   + (f", ticker={resolved}" if resolved else ", no ticker")
                   + (f", artifact_types={artifact_types}" if artifact_types else ""),
        )
    )

    # Bail out early on questions this assistant has no business answering.
    # Searching anyway would return the least-bad chunk of an unrelated document
    # and make an off-topic answer look sourced.
    if not in_scope(question, intent, resolved):
        ev.out_of_scope = True
        ev.trace.append(
            RetrievalStep(
                step="scope_check",
                detail="question uses no QuantML vocabulary; skipping retrieval",
            )
        )
        ev.warnings.append(
            "This question is outside what QuantML's artifacts cover, so no "
            "evidence was retrieved."
        )
        return ev

    # --- exact lookups, chosen by intent ---
    if resolved:
        signal = ev.call("get_latest_signal", ticker=resolved)
        if signal.get("ok"):
            ev.signal_context = signal
            # the premise check: correct the question rather than answer it
            claimed = _claimed_signal(question)
            if claimed and claimed != signal["signal"]:
                ev.warnings.append(
                    f"The question describes {resolved} as a {claimed} signal, but the "
                    f"current signal is {signal['signal']}. The answer corrects this "
                    f"rather than explaining a signal that was not issued."
                )
        if intent in ("signal_explanation", "trust_limitations", "risk", "general"):
            ev.call("get_top_shap_drivers", ticker=resolved)
        if intent in ("risk", "signal_explanation", "general"):
            ev.call("get_risk_summary", ticker=resolved)
        if intent in ("backtest_costs", "signal_explanation"):
            ev.call("get_backtest_summary", ticker=resolved)

    if intent in ("trust_limitations", "validation", "certainty_request", "general",
                  "signal_explanation"):
        ev.call("get_model_metrics", model_version=model_version)
    if intent in ("backtest_costs", "trust_limitations", "certainty_request", "validation"):
        if not ev.tool_result("get_backtest_summary"):
            ev.call("get_backtest_summary", model_version=model_version)
    if intent == "coverage":
        ev.call("get_signal_distribution")

    if intent == "feature_definition":
        for name in _feature_candidates(question):
            result = ev.call("get_feature_definition", feature_name=name)
            if result.get("ok"):
                break

    # --- search for the explanatory material ---
    filters = {"model_version": model_version, "run_id": run_id}

    if resolved:
        # this name's own artifacts first, so they can't be crowded out
        ticker_hits = _search(ev, store, question, top_k=3, filters={"ticker": resolved})
        ev.chunks.extend(ticker_hits)

    if artifact_types:
        typed = _search(
            ev, store, question,
            top_k=top_k,
            filters={**filters, "artifact_type": artifact_types},
        )
        ev.chunks.extend(typed)

    # a general sweep fills the gap when the typed search came back thin
    if len(ev.chunks) < top_k:
        ev.chunks.extend(
            _search(ev, store, question, top_k=top_k - len(ev.chunks) + 2, filters=filters)
        )

    # de-duplicate, keeping the best-scoring copy of each chunk
    seen: dict[str, object] = {}
    for hit in ev.chunks:
        prev = seen.get(hit.chunk.chunk_id)
        if prev is None or hit.similarity > prev.similarity:
            seen[hit.chunk.chunk_id] = hit
    ev.chunks = sorted(seen.values(), key=lambda h: h.similarity, reverse=True)[: top_k + 3]

    if not ev.has_evidence():
        ev.warnings.append(
            "No matching QuantML artifacts were found for this question."
        )
    return ev


def _search(ev: Evidence, store: VectorStore, question: str, top_k: int,
            filters: dict | None) -> list:
    embedder = get_embedder_for_store(store)
    vector = embedder.embed([question])[0]
    hits = store.search(question, vector, top_k=top_k, filters=filters)
    active = {k: v for k, v in (filters or {}).items() if v}
    ev.trace.append(
        RetrievalStep(
            step="vector_search",
            detail=f"top_k={top_k}, filters={active or 'none'}",
            result_count=len(hits),
        )
    )
    return hits


def get_embedder_for_store(store: VectorStore):
    """Use whatever embedder built the index, or vectors won't be comparable."""
    from config import settings

    if store.embedder_name == "hashing-v1":
        return get_embedder("hashing")
    return get_embedder(settings.research_embedding_provider, store.embedder_name)


def _feature_candidates(question: str) -> list[str]:
    """Guess which feature is being asked about, best guess first."""
    q = question.lower()
    found = re.findall(r"\b[a-z]+_[a-z0-9_]+\b", q)  # snake_case looks like a key
    for alias in tools.FEATURE_ALIASES:
        if alias in q:
            found.append(alias)
    # readable labels, e.g. "20-day momentum"
    found.extend(re.findall(r"\b\d+[- ]day \w+\b", q))
    for word in ("momentum", "volatility", "rsi", "macd", "atr", "bollinger",
                 "volume", "skew", "kurtosis", "gap"):
        if word in q:
            found.append(word)
    seen, out = set(), []
    for f in found:
        if f not in seen:
            seen.add(f)
            out.append(f)
    return out or [question.strip()]
