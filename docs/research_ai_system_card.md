# Research AI — system card

What this system is for, what it is not for, and how it fails.

QuantML is a portfolio and research project. It is not a product, it is not
regulated, and nothing in it has been reviewed by anyone qualified to give
financial advice.

---

## Intended use

Explaining machine learning output to someone trying to understand it.

Specifically: what signal the model produced, which features moved it and in
which direction, what the validation and backtest evidence supports, what the
risk layer did with it, and what would make any of it unreliable.

The intended user is a developer, researcher or reviewer inspecting QuantML —
someone who wants to know whether the modelling is sound and how the pieces fit
together.

Every answer carries the line *"This is a model-generated research explanation,
not investment advice."*

---

## Non-goals

**Investment advice.** It will not tell anyone what to buy, sell or hold, and
refuses when asked. It has no knowledge of anyone's circumstances, and giving
personalised financial advice is regulated activity that this project has no
standing to perform.

**Price prediction.** The model ranks stocks relative to each other on a 5-day
horizon. The assistant quotes that ranking; it does not forecast prices.

**Company analysis.** The model reads price and volume only. It has no view on
whether a company is well run, cheap, or has good prospects, and neither does
the assistant.

**Trade execution.** It cannot place orders. Nothing in QuantML can — live
trading is disabled by a flag that has to be deliberately switched on.

**A general finance assistant.** Questions outside QuantML's own artifacts are
refused rather than answered from the language model's background knowledge.

---

## Financial disclaimer

Nothing produced by this system is investment advice, a recommendation, or an
offer or solicitation to buy or sell any security.

The signals it explains come from a model with a small, measured edge —
out-of-sample AUC in the low 0.50s against 0.50 for chance. In the backtest it
underperformed simply holding the benchmark after costs. Past simulated
performance does not indicate future results, and these are simulated fills, not
real trades.

Anyone acting on this does so at their own risk. Consult a licensed advisor.

---

## Risks

### Hallucination

**What could happen.** The language model states a figure, date or feature that
is not in the evidence, in a fluent and plausible sentence.

**What is done.** Numbers are computed by deterministic lookups and passed in
pre-formatted, so nothing needs calculating. The prompt forbids invented figures
and requires citations. After generation, `grounding.py` compares every number in
the answer against the evidence and flags what does not appear.

**Residual risk.** The check is a heuristic. It tolerates restatement (`0.0883`
as `8.8%`), so an invented figure that happens to resemble a real one can slip
through. It can also flag a legitimate rephrasing. In mock mode this risk is
near zero, because the answer is assembled from the evidence rather than
generated; enabling a real LLM reintroduces it.

### False premise

**What could happen.** Someone asks why a stock got a BUY when it did not, and
the assistant explains reasoning behind a signal that was never issued. This is
the most damaging failure available to the system: it manufactures a rationale
for something that did not happen, and it looks completely convincing.

**What is done.** Claims about a signal in the question are checked against the
artifact. A mismatch produces an explicit correction before anything else.

**Residual risk.** Detection is pattern based and covers assertions about
BUY/HOLD/AVOID. Other false premises — about performance, dates or features —
are not specifically detected, though the general grounding rules discourage
going along with them.

### Stale data

**What could happen.** The index is built once and cached. If the pipeline
re-runs, the assistant keeps answering from the previous snapshot and confidently
quotes superseded numbers.

**What is done.** Every signal answer carries the `generatedAt` timestamp of the
artifact it came from. `POST /api/research/ingest` rebuilds.

**Residual risk.** Real. Nothing watches the filesystem, and nothing warns that
an artifact is old. Re-ingestion after a pipeline run is a manual step, and in a
deployment it should be wired into the pipeline itself.

### Model limitation risks

The underlying model sees only price and volume. It has no fundamentals, news,
earnings or filings. It cannot know about a scheduled event, and it learned from
a universe built from a current list of large NASDAQ names, so companies that
failed are absent from its history.

The assistant states these limitations, but stating a limitation is not the same
as the reader absorbing it. A well-written explanation of a weak signal can read
as more authoritative than the signal deserves. Confidence near 33% is flagged
explicitly for this reason, since with three classes that is the level meaning no
opinion at all.

### Over-trust from fluency

Well-formatted output with citations and section headings reads as more
authoritative than the underlying evidence supports. The citations are real and
the numbers are exact, but a small statistical edge presented in confident prose
can be mistaken for a strong conclusion.

Countermeasures: chance baselines travel alongside every metric, opposing
attribution drivers are surfaced rather than hidden, and every answer includes a
"what could make this wrong" section.

### Retrieval failure

Search can return the wrong passage, and a relevant document can be missed. The
default hashing embedder matches vocabulary rather than meaning, so a question
using different words for the same concept may not find it.

Mitigations: hybrid keyword scoring, metadata filtering, and the exact lookups,
which do not depend on retrieval succeeding. The full retrieval trace is returned
so a wrong answer can be diagnosed rather than guessed at.

---

## Privacy and security

**No user data is stored.** Questions are processed and returned. Nothing is
logged to disk, retained, or used for training.

**Keys are never returned.** `/api/research/health` reports whether a key is
configured, never its value. Keys are read from environment variables and are
gitignored.

**Questions leave the machine only if a real LLM provider is enabled.** In the
default mock mode nothing is sent anywhere. With `RESEARCH_LLM_PROVIDER=openai`
or `gemini`, the question and the retrieved evidence are sent to that provider
and are subject to their retention policy.

**The corpus is not sensitive.** It contains model output and project
documentation, all of which is already in the repository.

**Prompt injection.** Retrieved text is placed in the prompt. The corpus is
authored and the generated artifacts come from the pipeline, so there is no
untrusted input path today. This changes the moment external documents — filings,
news — are ingested, and that would need the retrieved content treated as
untrusted data rather than instructions.

**No authentication.** The endpoints are unauthenticated, as is the rest of the
QuantML API. Acceptable for local use, not for a public deployment.

---

## Evaluation limitations

The eval suite is 18 cases. That is enough to catch regressions in routing,
retrieval, citation and refusal, and nowhere near enough to characterise
behaviour across the space of questions people actually ask.

It checks structure, not quality: that the right artifacts were retrieved, the
right tools ran, citations and the disclaimer are present, refusals happen where
required, and no unsupported figures appear. It cannot tell whether an
explanation is insightful, clear, or appropriately hedged.

It runs in mock mode, so it measures retrieval and grounding, not generation.
Enabling a real LLM changes answer quality and reintroduces hallucination risk
that these tests do not cover.

The cases were written by the same author as the system, which is the weakest
form of evaluation there is. An independent set of questions would find failures
this one does not.

There is no measurement of how a reader interprets the answers, which for a
system whose entire purpose is explanation is the thing that most matters.

---

## Deployment considerations

Before this ran anywhere real, at minimum:

**Authentication and rate limiting.** The endpoints are open, and enabling a real
LLM makes an open endpoint a cost liability.

**Automatic re-ingestion** wired into the pipeline, so the index cannot silently
serve stale artifacts.

**Freshness limits.** Refuse to answer from artifacts older than some threshold
rather than quoting them without comment.

**Answer logging** for auditing what the system told people, balanced against the
privacy position above.

**A human review pass** over generated answers before any non-technical audience
sees them.

**Legal review.** An automated system explaining trading signals to the public
sits close to regulated territory regardless of how many disclaimers it carries.

**Monitoring** on grounding warning rates, refusal rates and latency, since a
rise in any of them indicates retrieval or generation quality has moved.

None of this is in place. This is a portfolio project running locally, and the
gap between that and a deployed system is the content of this section.
