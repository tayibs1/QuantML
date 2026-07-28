"""
Tests for the Research AI assistant.

Two situations get covered, because both are real. On a cold checkout there is no
data/ folder and the assistant has only its committed corpus — that is what CI
sees, and it must still answer methodology questions. With pipeline output
present it can also answer about specific stocks, so those tests point the config
at a temporary folder holding small fixture artifacts.

Nothing here needs a network, an API key or a model download.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from research import chunking, grounding, ingest, orchestrator, prompt, registry, tools
from research.embeddings import HashingEmbedder, get_embedder
from research.types import Artifact
from research.vectorstore import VectorStore

# --- fixture artifacts --------------------------------------------------------
# The JSON under tests/fixtures/research stands in for data/, which is gitignored
# and absent on a fresh clone. The evaluation harness reads the same files, so
# tests and eval scores describe the same world.

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "research"


def _fixture(*parts: str) -> dict:
    return json.loads((FIXTURE_DIR.joinpath(*parts)).read_text(encoding="utf-8"))


@pytest.fixture
def artifact_dir(tmp_path, monkeypatch):
    """Point the config at a copy of the fixture artifacts.

    The real data/ folder is gitignored and absent in CI, so tests that need
    pipeline output have to bring their own. It's copied rather than used in
    place so a test can modify it without touching the committed files.
    """
    from config import settings

    shutil.copytree(FIXTURE_DIR, tmp_path, dirs_exist_ok=True)
    (tmp_path / "vectorstore").mkdir(parents=True, exist_ok=True)

    cls = type(settings)
    for name, target in (
        ("data_dir", tmp_path),
        ("signals_dir", tmp_path / "signals"),
        ("models_dir", tmp_path / "models"),
        ("vectorstore_dir", tmp_path / "vectorstore"),
    ):
        monkeypatch.setattr(cls, name, property(lambda self, t=target: t))

    # Pin the numpy store: opening a fresh persistent Chroma client per test
    # crashes its native layer. The Chroma path is exercised by running the app,
    # not by the unit tests.
    monkeypatch.setattr(settings, "research_vector_backend", "numpy")

    tools._feature_sections.cache_clear()
    ingest.reset_cache()
    yield tmp_path
    ingest.reset_cache()


@pytest.fixture
def cold_checkout(tmp_path, monkeypatch):
    """No pipeline output at all — the state of a fresh clone and of CI."""
    from config import settings

    empty = tmp_path / "empty"
    (empty / "vectorstore").mkdir(parents=True)
    cls = type(settings)
    for name, target in (
        ("data_dir", empty),
        ("signals_dir", empty / "signals"),
        ("models_dir", empty / "models"),
        ("vectorstore_dir", empty / "vectorstore"),
    ):
        monkeypatch.setattr(cls, name, property(lambda self, t=target: t))
    monkeypatch.setattr(settings, "research_vector_backend", "numpy")
    ingest.reset_cache()
    yield empty
    ingest.reset_cache()


# --- chunking -----------------------------------------------------------------

def test_chunk_ids_are_stable_across_runs():
    """Rebuilding the index must not invalidate citations in a stored answer."""
    artifact = Artifact(
        artifact_id="corpus:test", artifact_type="documentation", title="Test",
        text="## One\n\n" + "alpha " * 40 + "\n\n## Two\n\n" + "beta " * 40,
        source_path="test.md",
    )
    first = [c.chunk_id for c in chunking.chunk_artifact(artifact)]
    second = [c.chunk_id for c in chunking.chunk_artifact(artifact)]
    assert first == second
    assert first == ["corpus:test#0", "corpus:test#1"]


def test_chunking_splits_on_headings_and_keeps_metadata():
    artifact = Artifact(
        artifact_id="signal:NVDA", artifact_type="latest_signal", title="NVDA",
        text="## Alpha\n\n" + "x " * 40 + "\n\n## Beta\n\n" + "y " * 40,
        source_path="data/signals/latest.json", ticker="NVDA",
        model_version="XGBoost-v3",
    )
    chunks = chunking.chunk_artifact(artifact)
    assert len(chunks) == 2
    assert {c.heading for c in chunks} == {"Alpha", "Beta"}
    # metadata has to survive onto every chunk or filtering breaks
    assert all(c.ticker == "NVDA" for c in chunks)
    assert all(c.model_version == "XGBoost-v3" for c in chunks)


def test_short_artifact_still_produces_one_chunk():
    artifact = Artifact(
        artifact_id="tiny:1", artifact_type="documentation", title="Tiny",
        text="short", source_path="x.md",
    )
    assert len(chunking.chunk_artifact(artifact)) == 1


# --- embeddings ---------------------------------------------------------------

def test_hashing_embedder_is_deterministic():
    """The index is written by one process and read by another, so identical text
    has to embed identically every time."""
    a = HashingEmbedder().embed(["max drawdown and sharpe ratio"])
    b = HashingEmbedder().embed(["max drawdown and sharpe ratio"])
    assert (a == b).all()


def test_hashing_embedder_separates_related_from_unrelated():
    emb = HashingEmbedder()
    vectors = emb.embed([
        "walk-forward validation prevents lookahead leakage",
        "walk-forward validation and leakage in model testing",
        "bollinger bands measure price position in a range",
    ])
    related = float(vectors[0] @ vectors[1])
    unrelated = float(vectors[0] @ vectors[2])
    assert related > unrelated


def test_embedder_falls_back_when_provider_unavailable():
    """A missing package should cost answer quality, not take the endpoint down."""
    embedder = get_embedder("sentence-transformers", "definitely-not-a-real-model")
    assert isinstance(embedder, HashingEmbedder)


# --- registry -----------------------------------------------------------------

def test_corpus_is_available_without_any_pipeline_output(cold_checkout):
    """A fresh clone must still be able to explain the methodology."""
    found = registry.discover()
    types = {a.artifact_type for a in found}
    assert {"feature_dictionary", "validation_report", "backtest_report",
            "risk_report", "model_card"} <= types
    assert not [a for a in found if a.artifact_type == "latest_signal"]


def test_registry_picks_up_pipeline_artifacts(artifact_dir):
    found = registry.discover()
    ids = {a.artifact_id for a in found}
    assert "signal:NVDA" in ids
    assert "shap:NVDA" in ids
    assert "backtest:latest" in ids
    assert "model_card:xgboost-v3" in ids

    signal = next(a for a in found if a.artifact_id == "signal:NVDA")
    assert signal.ticker == "NVDA"
    assert signal.numeric["confidence"] == 36.5


def test_feature_dictionary_covers_every_model_feature():
    """The dictionary and the model's feature list must not drift apart.

    They live in different places on purpose — the model side can't import the
    backend — so this is the check that keeps them honest.
    """
    from ml.features.build import FEATURE_COLS

    documented = set(tools._feature_sections())
    missing = set(FEATURE_COLS) - documented
    assert not missing, f"features with no dictionary entry: {sorted(missing)}"


# --- vector store -------------------------------------------------------------

def _build_store(artifacts):
    chunks = chunking.chunk_all(artifacts)
    embedder = HashingEmbedder()
    vectors = embedder.embed([f"{c.title}\n{c.text}" for c in chunks])
    return VectorStore(chunks, vectors, embedder.name)


def test_metadata_filter_restricts_results_to_one_ticker(artifact_dir):
    store = _build_store(registry.discover())
    query = "why this signal"
    vector = HashingEmbedder().embed([query])[0]
    hits = store.search(query, vector, top_k=10, filters={"ticker": "NVDA"})
    assert hits
    assert all(h.chunk.ticker == "NVDA" for h in hits)


def test_metadata_filter_accepts_a_list_of_types(artifact_dir):
    store = _build_store(registry.discover())
    vector = HashingEmbedder().embed(["validation"])[0]
    hits = store.search(
        "validation", vector, top_k=10,
        filters={"artifact_type": ["validation_report", "backtest_report"]},
    )
    assert hits
    assert all(
        h.chunk.artifact_type in {"validation_report", "backtest_report"} for h in hits
    )


def test_search_returns_source_paths_and_chunk_ids(artifact_dir):
    store = _build_store(registry.discover())
    vector = HashingEmbedder().embed(["transaction costs"])[0]
    hits = store.search("transaction costs", vector, top_k=3)
    assert hits
    for hit in hits:
        assert hit.chunk.chunk_id
        assert hit.chunk.source_path
        assert 0.0 <= abs(hit.similarity) <= 1.0


def test_impossible_filter_returns_nothing_rather_than_falling_back(artifact_dir):
    """A filter that matches nothing must return nothing. Quietly widening the
    search would produce answers about the wrong stock."""
    store = _build_store(registry.discover())
    vector = HashingEmbedder().embed(["anything"])[0]
    assert store.search("anything", vector, top_k=5, filters={"ticker": "NOTREAL"}) == []


def test_index_round_trips_through_disk(artifact_dir):
    store = _build_store(registry.discover())
    store.save(artifact_dir / "vectorstore")
    loaded = VectorStore.load(artifact_dir / "vectorstore")
    assert loaded is not None
    assert len(loaded.chunks) == len(store.chunks)
    assert loaded.chunks[0].chunk_id == store.chunks[0].chunk_id


# --- structured tools ---------------------------------------------------------

def test_latest_signal_returns_exact_values(artifact_dir):
    result = tools.get_latest_signal("NVDA")
    assert result["ok"]
    assert result["signal"] == "HOLD"
    assert result["confidence"] == 36.5
    # the guessing floor travels with the number so it can't be read as high
    assert result["chanceLevel"] == 33.3


def test_latest_signal_is_case_insensitive(artifact_dir):
    assert tools.get_latest_signal("nvda")["ticker"] == "NVDA"


def test_unknown_ticker_reports_missing_instead_of_guessing(artifact_dir):
    result = tools.get_latest_signal("ZZZZ")
    assert result["ok"] is False
    assert "not in the scored universe" in result["reason"]


def test_shap_drivers_split_by_direction(artifact_dir):
    result = tools.get_top_shap_drivers("NVDA")
    assert result["ok"]
    assert all(d["contribution"] >= 0 for d in result["supporting"])
    assert all(d["contribution"] < 0 for d in result["opposing"])
    assert result["opposing"], "opposing drivers are the interesting half"


def test_model_metrics_carry_their_chance_baselines(artifact_dir):
    result = tools.get_model_metrics()
    assert result["ok"]
    assert result["auc"] == 0.5404
    # an AUC of 0.54 only means anything next to 0.50
    assert result["baselines"] == {"accuracy": 33.3, "auc": 0.50}


def test_backtest_summary_reports_round_trip_costs(artifact_dir):
    result = tools.get_backtest_summary()
    assert result["ok"]
    assert result["costsBps"]["roundTrip"] == 13.0
    assert result["netOfCosts"] is True


def test_backtest_summary_filters_trades_by_ticker(artifact_dir):
    result = tools.get_backtest_summary(ticker="AMD")
    # the fixture ledger holds two AMD trades, one up and one down
    assert result["tickerTrades"]["count"] == 2
    assert result["tickerTrades"]["winRate"] == 50.0

    missing = tools.get_backtest_summary(ticker="NVDA")
    assert missing["tickerTrades"]["count"] == 0
    # absence from a sampled ledger isn't evidence the name was never held
    assert "not proof" in missing["tickerTrades"]["note"]


def test_risk_summary_explains_why_a_non_buy_gets_no_position(artifact_dir):
    result = tools.get_risk_summary("NVDA")
    assert result["ok"]
    assert result["inProposedBook"] is False
    assert "long-only" in result["note"]
    assert result["limits"]["maxNameWeight"] == 0.20


def test_feature_definition_resolves_aliases():
    """People type momentum_20d; the model calls it ret_20."""
    assert tools.get_feature_definition("momentum_20d")["key"] == "ret_20"
    assert tools.get_feature_definition("ret_20")["key"] == "ret_20"
    assert tools.get_feature_definition("20-day momentum")["key"] == "ret_20"


def test_unknown_feature_lists_what_is_available():
    result = tools.get_feature_definition("sentiment_score")
    assert result["ok"] is False
    assert "ret_20" in result["available"]


def test_tools_report_missing_data_without_raising(cold_checkout):
    for result in (
        tools.get_latest_signal("NVDA"),
        tools.get_top_shap_drivers("NVDA"),
        tools.get_backtest_summary(),
    ):
        assert result["ok"] is False
        assert result["reason"]


# --- orchestration ------------------------------------------------------------

@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Why did the model give NVDA a BUY signal?", "signal_explanation"),
        ("What does momentum_20d mean?", "feature_definition"),
        ("Can I trust this model?", "trust_limitations"),
        ("How did the model perform after transaction costs?", "backtest_costs"),
        ("What does walk-forward validation show?", "validation"),
        ("Should I buy AMD?", "advice_request"),
        ("Tell me the exact return next week", "certainty_request"),
        ("Is this a guaranteed profit?", "certainty_request"),
    ],
)
def test_question_routing(question, expected):
    assert orchestrator.classify(question)[0] == expected


def test_ticker_is_resolved_from_symbol_or_company_name(artifact_dir):
    assert orchestrator.resolve_ticker("Why is NVDA a hold?") == "NVDA"
    assert orchestrator.resolve_ticker("what about nvidia") == "NVDA"
    # words shaped like tickers but obviously not tickers
    assert orchestrator.resolve_ticker("What is AI doing to the model?") is None


def test_off_topic_questions_are_refused_before_retrieval():
    assert orchestrator.in_scope("What does walk-forward mean?", "validation", None)
    assert not orchestrator.in_scope("What is the capital of France?", "general", None)
    assert not orchestrator.in_scope("write me a poem", "general", None)


def test_false_premise_is_flagged(artifact_dir):
    """NVDA is a HOLD. Explaining a BUY that was never issued is the worst
    failure this system can have, so it gets its own check."""
    store = ingest.get_index()
    ev = orchestrator.gather("Why did the model give NVDA a BUY signal?", store)
    assert ev.warnings
    assert "BUY" in ev.warnings[0] and "HOLD" in ev.warnings[0]


def test_correct_premise_is_not_flagged(artifact_dir):
    store = ingest.get_index()
    ev = orchestrator.gather("Why did AMD get a BUY signal?", store)
    assert not any("describes" in w for w in ev.warnings)


def test_signal_question_gathers_signal_and_attribution(artifact_dir):
    store = ingest.get_index()
    ev = orchestrator.gather("Why did AMD get its signal?", store)
    called = {c.tool for c in ev.tool_calls if c.ok}
    assert {"get_latest_signal", "get_top_shap_drivers"} <= called


# --- prompt -------------------------------------------------------------------

def test_prompt_carries_the_grounding_contract(artifact_dir):
    store = ingest.get_index()
    ev = orchestrator.gather("Why did AMD get its signal?", store)
    system, user, refs = prompt.build(ev)

    assert prompt.DISCLAIMER in system
    assert "Cite the evidence" in system
    assert "must not appear" in system
    assert "QUESTION" in user
    assert "STRUCTURED DATA" in user
    assert "RETRIEVED EVIDENCE" in user
    assert refs
    assert all(r["tag"] for r in refs)


def test_prompt_tags_are_unique(artifact_dir):
    store = ingest.get_index()
    ev = orchestrator.gather("Why did AMD get its signal?", store)
    _, _, refs = prompt.build(ev)
    tags = [r["tag"] for r in refs]
    assert len(tags) == len(set(tags))


def test_prompt_surfaces_unavailable_lookups(cold_checkout):
    store = ingest.get_index()
    ev = orchestrator.gather("What is NVDA's signal?", store, ticker="NVDA")
    _, user, _ = prompt.build(ev)
    assert "UNAVAILABLE" in user


# --- grounding ----------------------------------------------------------------

def test_grounding_flags_a_missing_disclaimer():
    warnings = grounding.check("The signal is HOLD [S1].", [{"tag": "S1"}], "", "", True)
    assert any("disclaimer" in w for w in warnings)


def test_grounding_flags_invented_numbers():
    answer = f"Sharpe was 4.71 and CAGR 92.3%. {prompt.DISCLAIMER} [S1]"
    warnings = grounding.check(
        answer, [{"tag": "S1"}], '{"sharpe": 0.51}', "cagr 0.0883", True
    )
    assert any("not in the retrieved evidence" in w for w in warnings)


def test_grounding_accepts_a_fraction_restated_as_a_percentage():
    """0.0883 quoted as 8.8% is rephrasing, not inventing."""
    answer = f"CAGR was 8.8% net of costs [S1]. {prompt.DISCLAIMER}"
    warnings = grounding.check(answer, [{"tag": "S1"}], '{"cagr": 0.0883}', "", True)
    assert not any("not in the retrieved evidence" in w for w in warnings)


def test_grounding_ignores_digits_inside_identifiers():
    """rsi_14 and chunk ids are names, not claims."""
    answer = (
        f"Drivers were rsi_14 and ret_20 [E1]. See chunk corpus:features#12. "
        f"{prompt.DISCLAIMER}"
    )
    warnings = grounding.check(answer, [{"tag": "E1"}], "{}", "rsi_14 ret_20", True)
    assert not any("not in the retrieved evidence" in w for w in warnings)


def test_grounding_flags_advice_language():
    answer = f"You should buy this stock. {prompt.DISCLAIMER} [S1]"
    warnings = grounding.check(answer, [{"tag": "S1"}], "", "", True)
    assert any("advice" in w or "guarantee" in w for w in warnings)


def test_grounding_flags_uncited_answers():
    answer = f"The model is excellent. {prompt.DISCLAIMER}"
    warnings = grounding.check(answer, [{"tag": "S1"}], "", "", True)
    assert any("cites no sources" in w for w in warnings)


def test_grounding_flags_citations_that_were_never_supplied():
    answer = f"As shown [E9]. {prompt.DISCLAIMER}"
    warnings = grounding.check(answer, [{"tag": "S1"}], "", "", True)
    assert any("E9" in w for w in warnings)


# --- end to end ---------------------------------------------------------------

def test_answer_is_grounded_cited_and_disclaimed(artifact_dir):
    result = __import__("research").answer("Why did AMD get a BUY signal?")
    assert result["grounded"]
    assert prompt.DISCLAIMER in result["answer"]
    assert result["sources"]
    assert result["signal_context"]["signal"] == "BUY"
    assert result["llm"]["provider"] == "mock"
    assert result["latency_ms"] > 0


def test_answer_reports_both_supporting_and_opposing_drivers(artifact_dir):
    result = __import__("research").answer("Which features drove AMD's prediction?")
    assert "120-day momentum" in result["answer"]
    drivers = result["signal_context"]["drivers"]
    assert drivers["supporting"] and drivers["opposing"]


def test_answer_abstains_when_off_topic(artifact_dir):
    result = __import__("research").answer("What is the capital of France?")
    assert result["grounded"] is False
    assert "can't answer" in result["answer"].lower()
    assert prompt.DISCLAIMER in result["answer"]


def test_answer_declines_to_give_advice(artifact_dir):
    result = __import__("research").answer("Should I buy AMD?")
    assert result["intent"] == "advice_request"
    assert "can't tell you what to do" in result["answer"].lower()


def test_answer_refuses_to_promise_certainty(artifact_dir):
    result = __import__("research").answer("What is the exact return AMD will make?")
    assert result["intent"] == "certainty_request"
    assert "no certainty" in result["answer"].lower()


def test_answer_works_on_a_cold_checkout(cold_checkout):
    """No pipeline output, but methodology questions must still work."""
    result = __import__("research").answer("What does walk-forward validation show?")
    assert result["grounded"]
    assert result["sources"]
    assert prompt.DISCLAIMER in result["answer"]


def test_missing_signal_data_is_reported_not_invented(cold_checkout):
    result = __import__("research").answer("What is NVDA's current signal?", ticker="NVDA")
    failed = [c for c in result["tool_calls"] if not c["ok"]]
    assert failed, "the lookup should fail rather than return a made-up signal"
    assert "36.5" not in result["answer"]


def test_retrieval_trace_is_returned_for_auditing(artifact_dir):
    result = __import__("research").answer("Why did AMD get a BUY signal?")
    steps = {s["step"] for s in result["retrieval_trace"]}
    assert "classify" in steps
    assert any(s.startswith("tool:") for s in steps)
    assert "vector_search" in steps


def test_mock_mode_needs_no_api_key(artifact_dir, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "research_llm_provider", "mock")
    result = __import__("research").answer("What are the model's limitations?")
    assert result["llm"]["provider"] == "mock"
    assert result["answer"]


# --- api ----------------------------------------------------------------------

@pytest.fixture
def client():
    from main import app

    return TestClient(app)


def test_query_endpoint_returns_answer_sources_and_trace(client, artifact_dir):
    response = client.post(
        "/api/research/query",
        json={"question": "Why did AMD get a BUY signal?", "ticker": "AMD"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"]
    assert body["sources"]
    assert body["retrieval_trace"]
    assert body["signal_context"]["ticker"] == "AMD"
    assert prompt.DISCLAIMER in body["answer"]


def test_query_endpoint_honours_top_k(client, artifact_dir):
    body = client.post(
        "/api/research/query",
        json={"question": "What does walk-forward validation show?", "top_k": 2},
    ).json()
    assert len(body["evidence"]) <= 5  # top_k plus the small overflow allowance


def test_health_endpoint_reports_index_and_mode(client):
    body = client.get("/api/research/health").json()
    assert body["indexReady"] is True
    assert body["llm"]["mockMode"] is True
    assert body["index"]["chunks"] > 0


def test_health_never_leaks_a_key(client):
    body = client.get("/api/research/health").json()
    assert set(body["llm"]) >= {"provider", "mockMode", "keyConfigured"}
    assert "apiKey" not in json.dumps(body)


def test_artifacts_endpoint_lists_indexed_material(client):
    body = client.get("/api/research/artifacts").json()
    assert body["count"] > 0
    assert body["byType"]
    assert all("artifact_id" in a for a in body["artifacts"])


def test_examples_endpoint_returns_prompts(client):
    body = client.get("/api/research/examples").json()
    assert len(body["examples"]) >= 5


def test_ingest_endpoint_rebuilds_the_index(client, artifact_dir):
    body = client.post("/api/research/ingest").json()
    assert body["status"] == "ok"
    assert body["chunks"] > 0
    assert body["artifacts"] > 0


# --- evaluation harness -------------------------------------------------------

def test_eval_set_is_well_formed():
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "data" / "research_ai_eval_set.jsonl"
    cases = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
             if line.strip()]
    assert len(cases) >= 10
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    for case in cases:
        assert case["question"]
        assert isinstance(case.get("expected_artifact_types", []), list)
    # the behaviours most worth protecting have to stay covered
    assert any(c.get("should_abstain") for c in cases)
    assert any(c.get("expect_premise_correction") for c in cases)
    assert any(c.get("expect_intent") == "advice_request" for c in cases)


def test_evaluation_script_runs_end_to_end(tmp_path):
    """The harness has to work in mock mode with no keys, or CI can't use it."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "eval.md"
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "evaluate_research_ai.py"),
         "--out", str(out)],
        capture_output=True, text=True, cwd=root, timeout=300,
    )
    assert result.returncode == 0, result.stderr
    report = out.read_text(encoding="utf-8")
    assert "Research AI evaluation" in report
    assert "Cases passed" in report


def test_legacy_research_endpoint_still_works(client, artifact_dir):
    """The dashboard chat used this shape before; it must not break."""
    body = client.post("/api/research", json={"prompt": "Why is AMD a BUY?"}).json()
    assert set(body) >= {"prompt", "answer", "sources", "signalContext", "confidence"}
    assert body["signalContext"]["ticker"] == "AMD"
