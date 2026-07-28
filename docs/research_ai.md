# Research AI

The assistant that explains QuantML's own output.

QuantML produces signals. Research AI explains where they came from, what
evidence supports them, and what would make them wrong — citing a specific
artifact for every claim.

---

## Why this is not a chatbot over documents

A language model asked "why is NVDA a BUY" will produce a fluent, confident,
entirely invented answer. It has read a great deal about markets and none of it
about this model. Pointing a generic retrieval chatbot at the repo does not fix
that, for two reasons.

**Search returns approximately relevant text.** For "what is NVDA's confidence",
approximately right is wrong. That number has to be looked up, not retrieved by
similarity.

**Retrieved text does not stop invention.** A model given a paragraph about
Sharpe ratios will happily state a Sharpe ratio that was not in it.

So the system is built around a split:

| | supplies | can it be wrong |
| --- | --- | --- |
| **Exact lookups** | every number | no — read straight from the artifact |
| **Vector search** | explanation and context | it can retrieve the wrong passage |
| **Generation** | the wording | checked afterwards against both |

Numbers never come from the language model. They arrive pre-computed, and the
answer is checked against them afterwards.

---

## Architecture

```
question
   |
   +-- classify intent, resolve ticker            orchestrator.py
   |     |
   |     +-- off topic? -> abstain, no retrieval
   |
   +-- exact lookups (the figures)                tools.py
   |     get_latest_signal, get_top_shap_drivers, get_model_metrics,
   |     get_backtest_summary, get_risk_summary, get_feature_definition
   |
   +-- filtered search (the explanation)          vectorstore.py
   |     dense + BM25, metadata filters, MMR rerank
   |
   +-- build grounded prompt                      prompt.py
   |
   +-- generate                                   llm.py    (mock | openai | gemini)
   |
   +-- check answer against evidence              grounding.py
   |
   answer + citations + trace + warnings
```

Files, all under `backend/research/`:

| File | Does |
| --- | --- |
| `registry.py` | Finds artifacts and attaches metadata |
| `chunking.py` | Splits them on headings into citable chunks |
| `embeddings.py` | Hashing (default) or sentence-transformers |
| `vectorstore.py` | Chroma or numpy, filtering, hybrid search, rerank |
| `ingest.py` | Builds and caches the index |
| `tools.py` | The six exact lookups |
| `orchestrator.py` | Question → retrieval plan |
| `prompt.py` | The grounding contract |
| `llm.py` | Answer generation, mock included |
| `grounding.py` | Post-answer verification |
| `service.py` | Ties it together |
| `corpus/` | Hand-written explanatory documents |

---

## What gets indexed

Two sources.

**`backend/research/corpus/`** ships with the repo: the feature dictionary,
signal glossary, validation methodology, backtest and cost methodology, risk
framework, model limitations, and how to read the attribution. These are
committed, so a fresh clone can explain the methodology before anything has run.

**`data/`** is discovered when the pipeline has produced it: live signals per
ticker, feature attribution per ticker, model cards, training metadata, backtest
reports, and the research studies (drift, calibration, out-of-distribution,
rolling window, regime).

Repo markdown (`README.md`, `docs/BACKEND.md`, and the per-package READMEs) is
indexed too.

A cold checkout indexes around 110 chunks. With pipeline output it is around 240.

**Not indexed, and worth being explicit about:** SEC filings, news, earnings
transcripts, analyst estimates, fundamentals. The model does not read them, so
the assistant cannot answer from them and says so.

### Adding a new artifact type

1. Add the type to `ArtifactType` in `types.py`.
2. Write a `_something_artifacts()` function in `registry.py` returning
   `Artifact` objects, and add it to the tuple in `discover()`.
3. Give it a `source_path` a reader can open, and put any exact figures in
   `numeric`.
4. Rebuild: `POST /api/research/ingest`.

For a hand-written explainer, just drop a markdown file into `corpus/` with front
matter naming its `artifact_type` and `title`. Nothing else is needed.

---

## Retrieval

**Metadata filtering runs before scoring.** Asking about NVDA never ranks the
other 55 names. Filters accept a value or a list, and are available on `ticker`,
`artifact_type`, `model_version` and `run_id`.

**Hybrid scoring.** Dense similarity carries most of the weight; BM25 keyword
matching contributes 35%, normalised against the best hit. Keywords matter here
because tickers and feature keys are exactly the tokens an embedder blurs into
their neighbours.

**MMR reranking** spreads results across documents. Without it, a question about
costs returns five overlapping chunks of the same page.

**Scope check.** Questions using no QuantML vocabulary are refused before
retrieval. This is a word-list check rather than a similarity threshold, because
with the default embedder "write me a poem" scores *higher* against this corpus
than a genuine question about trading costs. The similarity numbers do not
separate on-topic from off-topic, so they are not used to try.

---

## Grounding

Four things keep answers honest.

**Exact figures are pre-computed** and passed in as structured blocks. There is
nothing to calculate.

**The prompt requires citations** on every substantive claim, so an unsupported
sentence is visibly unsupported.

**Missing evidence is a valid answer.** The prompt says so explicitly, because
models invent rather than admit a gap unless told otherwise.

**The answer is checked afterwards** by `grounding.py`, which flags:

- figures not present in the evidence
- citation tags that were never supplied
- answers with no citations at all
- a missing disclaimer
- advice or guarantee language

The number check tolerates restatement: `0.0883` quoted as `8.8%` is rephrasing,
not invention. It ignores digits inside feature keys (`rsi_14`), chunk ids and
dates. Without those exemptions the warnings fill with noise and readers learn to
ignore them.

Warnings are shown, not enforced. A visible warning beats a silent rewrite.

### Premise correction

If a question asserts something the artifacts contradict — "why did the model
give NVDA a BUY" when NVDA is a HOLD — the assistant corrects it and answers the
corrected question.

This is the failure mode that matters most. An assistant that fluently explains
the reasoning behind a signal that was never issued is worse than one that
refuses to answer.

---

## Running it

Nothing below needs an API key.

```bash
pip install -r backend/requirements.txt
cd backend && uvicorn main:app --reload --port 8000
```

The index builds itself on first use. To rebuild after the pipeline runs:

```bash
curl -X POST http://localhost:8000/api/research/ingest
```

Point the dashboard at the backend in `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then `cd frontend && npm run dev` and open `/research`.

Without that variable the page falls back to the older snapshot route, which
still answers but has no cited artifacts. The header says which mode is live.

### Endpoints

| Endpoint | Does |
| --- | --- |
| `POST /api/research/query` | Ask a question, get answer + evidence + trace |
| `POST /api/research/ingest` | Rebuild the index |
| `GET /api/research/artifacts` | List what is indexed |
| `GET /api/research/examples` | Example questions for the UI |
| `GET /api/research/health` | Index status and active providers |
| `POST /api/research` | The original shape, kept working |

```bash
curl -X POST http://localhost:8000/api/research/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Why did the model give NVDA a BUY signal?", "ticker": "NVDA"}'
```

---

## Mock mode

The default. No keys, no downloads, no network.

**Mock LLM** writes the answer directly from the evidence. This is not a
placeholder: since every figure comes from the exact lookups and every citation
from retrieval, a templated answer is exactly as accurate as a generated one, and
it cannot hallucinate. What it lacks is fluency and the ability to handle a
question the templates did not anticipate.

**Hashing embedder** scatters words into fixed buckets. Deterministic across
machines and processes, which is what makes the tests meaningful. It matches on
shared vocabulary, not meaning — it cannot tell that "loss" and "drawdown" are
related.

**Numpy vector store** compares against everything. At a few hundred chunks that
is exact and instant.

### Upgrading

Set these in `.env`. Each is independent.

```bash
# better retrieval — downloads a model, no key
RESEARCH_EMBEDDING_PROVIDER=sentence-transformers

# real generation
RESEARCH_LLM_PROVIDER=openai        # or gemini
OPENAI_API_KEY=sk-...
RESEARCH_LLM_MODEL=gpt-4o-mini
```

For a persistent vector store, `pip install chromadb`. It is picked up
automatically once present, and `/api/research/health` reports which store is
active. It is deliberately not pinned in `backend/requirements.txt`: older
releases build `chroma-hnswlib` from source and need a C++ toolchain on Windows,
and current ones crash the process when several persistent clients are opened in
succession — which is what a test run does. Keeping it opt-in means a plain
`pip install -r` always works. `RESEARCH_VECTOR_BACKEND=numpy` pins the fallback
even when chromadb is installed.

If a provider fails at runtime the system falls back to mock rather than
erroring — a rate limit should cost fluency, not the answer. The response says
which provider actually ran.

Changing the embedder requires a re-ingest; vectors from different models are not
comparable.

---

## Evaluation

```bash
python scripts/evaluate_research_ai.py
python scripts/evaluate_research_ai.py --format csv --out reports/eval.csv
python scripts/evaluate_research_ai.py --strict   # non-zero exit on failure
```

18 cases in `data/research_ai_eval_set.jsonl`, each declaring expected artifact
types, expected tool calls, required keywords, whether it should abstain, and the
minimum citation count.

When `data/` has no pipeline output — a fresh clone, or CI — it falls back to the
committed artifacts in `tests/fixtures/research/`, the same ones the tests use.
The report says which source it read. That keeps the score reproducible, so a
failure means the assistant behaved differently rather than that the machine had
no data.

Current: **18/18 cases, 182/182 checks, ~5 ms median**, in both modes. It runs in
CI on every push with `--strict`.

It verifies the plumbing — right evidence retrieved, tools called, citations
present, disclaimer present, refusals where required, no unsupported figures. It
does not verify that explanations are *good*; that needs a human reading them.

---

## Tests

```bash
pytest tests/test_research_ai.py -q
```

66 tests covering chunk id stability, embedding determinism, metadata filtering,
each exact lookup, intent routing, premise correction, prompt construction,
grounding checks, abstention, refusal, and every endpoint.

They run in two states: a cold checkout with no `data/` (what CI sees, where only
the committed corpus is available) and a temp copy of `tests/fixtures/research/`
standing in for pipeline output. No network, no keys, no downloads.

---

## Limitations

**The corpus is small and self-referential.** It contains QuantML's output and
QuantML's own documentation. Questions outside that are refused.

**The default embedder is lexical.** It matches shared vocabulary, not meaning.
Synonyms not sharing words will not match. `sentence-transformers` fixes this.

**Intent classification is keyword based.** Inspectable and instant, but a novel
phrasing may route to a general search. The fallback is a broad search, not a
wrong answer.

**Grounding checks are heuristics.** The number check can miss an invented figure
that happens to resemble one in the evidence, and can flag a legitimate
restatement. It reduces hallucination; it does not eliminate it.

**The index is a snapshot.** It does not watch the filesystem. After the pipeline
runs, re-ingest.

**Mock answers are templated.** Predictable in shape and limited to anticipated
question types.

**Attribution explains, it does not justify.** SHAP says how the model reached an
output, not whether the output is right.

See `docs/research_ai_system_card.md` for intended use, risks and deployment
considerations.
