"""
Score the research assistant against a fixed set of questions.

    python scripts/evaluate_research_ai.py
    python scripts/evaluate_research_ai.py --format csv --out reports/eval.csv

Each question in the eval set says what a good answer looks like: which kinds of
artifact should be retrieved, which tools should run, whether it should refuse,
and what it must not do. The script runs them all and reports which checks passed.

It runs in mock mode by default, so it needs no API key and gives the same result
every time. That makes it useful as a regression test: change the retrieval or
the prompt, re-run this, and see what moved.

What it measures is plumbing, not prose. It checks that the right evidence was
retrieved, that answers carry citations and the disclaimer, that refusals happen
where they should, and that no unsupported figures crept in. It cannot tell you
whether an explanation is genuinely insightful — read those yourself.
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "backend"))

DEFAULT_EVAL_SET = REPO_ROOT / "data" / "research_ai_eval_set.jsonl"
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "research"


def use_fixtures_if_no_pipeline_output() -> str:
    """Fall back to the committed fixture artifacts when data/ is empty.

    data/ is gitignored, so on a fresh clone and in CI there are no signals to
    ask about and half the eval set would fail for the wrong reason. Pointing at
    fixtures instead keeps the run reproducible and makes a failure mean what it
    should: the assistant behaved differently, not that the machine had no data.
    """
    from config import settings

    if (settings.signals_dir / "latest.json").exists():
        return "data/"

    cls = type(settings)
    for name, target in (
        ("data_dir", FIXTURE_DIR),
        ("signals_dir", FIXTURE_DIR / "signals"),
        ("models_dir", FIXTURE_DIR / "models"),
        ("vectorstore_dir", REPO_ROOT / "data" / "vectorstore"),
    ):
        setattr(cls, name, property(lambda self, t=target: t))
    return "tests/fixtures/research (no pipeline output found)"


@dataclass
class Case:
    """One evaluated question and everything that was checked about it."""
    id: str
    question: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    latency_ms: float = 0.0
    intent: str = ""
    source_count: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failed

    def check(self, name: str, condition: bool) -> None:
        (self.passed if condition else self.failed).append(name)


def load_cases(path: Path) -> list[dict]:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("//"):
            cases.append(json.loads(line))
    return cases


def evaluate_one(spec: dict, latency_budget_ms: float) -> Case:
    import research
    from research.prompt import DISCLAIMER

    case = Case(id=spec["id"], question=spec["question"])

    started = time.perf_counter()
    result = research.answer(spec["question"], ticker=spec.get("ticker"))
    case.latency_ms = round((time.perf_counter() - started) * 1000, 1)
    case.intent = result["intent"]
    case.source_count = len(result["sources"])
    case.warnings = result["grounding_warnings"]

    answer_text = result["answer"].lower()

    # --- did it retrieve the right kind of evidence ---
    expected_types = set(spec.get("expected_artifact_types") or [])
    if expected_types:
        got = {s["artifact_type"] for s in result["sources"]}
        got |= {e["artifact_type"] for e in result["evidence"]}
        case.check(
            f"retrieved one of {sorted(expected_types)}",
            bool(expected_types & got),
        )

    # --- did the right exact lookups run ---
    for tool in spec.get("expected_tools") or []:
        ran = any(c["tool"] == tool and c["ok"] for c in result["tool_calls"])
        case.check(f"called {tool}", ran)

    # --- content ---
    for keyword in spec.get("expected_keywords") or []:
        case.check(f"mentions {keyword!r}", keyword.lower() in answer_text)

    # --- abstention and refusal ---
    if spec.get("should_abstain"):
        case.check("abstained", result["grounded"] is False)
        case.check(
            "said so plainly",
            "can't answer" in answer_text or "cannot answer" in answer_text,
        )
    else:
        case.check("did not abstain", result["grounded"] is True)

    if spec.get("expect_intent"):
        case.check(
            f"routed to {spec['expect_intent']}",
            result["intent"] == spec["expect_intent"],
        )

    if spec.get("expect_premise_correction"):
        case.check(
            "corrected the false premise",
            any("describes" in w and "but the current signal" in w
                for w in result["grounding_warnings"]),
        )

    if spec.get("expect_failed_tool"):
        case.check(
            "reported the lookup failure",
            any(not c["ok"] for c in result["tool_calls"]),
        )

    if spec.get("expect_missing_evidence"):
        # the point is that it must not answer from general knowledge
        case.check(
            "did not answer from outside the artifacts",
            "revenue" not in answer_text or "not" in answer_text,
        )

    # --- always required ---
    if spec.get("answer_must_include_disclaimer", True):
        case.check("carries the disclaimer", DISCLAIMER.lower() in answer_text)

    minimum = spec.get("expected_source_count_min", 0)
    case.check(f"cited at least {minimum} sources", case.source_count >= minimum)

    if minimum > 0:
        case.check(
            "answer contains citation tags",
            "[s" in answer_text or "[e" in answer_text,
        )

    unsupported = [w for w in result["grounding_warnings"]
                   if "not in the retrieved evidence" in w]
    case.check("no unsupported figures", not unsupported)

    advice = [w for w in result["grounding_warnings"]
              if "advice" in w or "guarantee" in w]
    case.check("no advice language", not advice)

    case.check(
        f"under {latency_budget_ms:.0f}ms", case.latency_ms <= latency_budget_ms
    )
    return case


def render_markdown(cases: list[Case], meta: dict) -> str:
    total_checks = sum(len(c.passed) + len(c.failed) for c in cases)
    passed_checks = sum(len(c.passed) for c in cases)
    latencies = [c.latency_ms for c in cases]
    cases_passed = sum(1 for c in cases if c.ok)

    lines = [
        "# Research AI evaluation",
        "",
        f"- Generated: {meta['generated_at']}",
        f"- LLM provider: `{meta['llm_provider']}`",
        f"- Embedder: `{meta['embedder']}`",
        f"- Artifacts from: `{meta['artifact_source']}`",
        f"- Index: {meta['chunks']} chunks across {meta['artifacts']} artifacts",
        "",
        "## Results",
        "",
        f"- Cases passed: **{cases_passed}/{len(cases)}**",
        f"- Checks passed: **{passed_checks}/{total_checks}**",
        f"- Median latency: {statistics.median(latencies):.0f} ms",
        f"- Slowest: {max(latencies):.0f} ms",
        "",
        "| Case | Intent | Sources | Latency | Checks | Result |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for c in cases:
        total = len(c.passed) + len(c.failed)
        lines.append(
            f"| `{c.id}` | {c.intent} | {c.source_count} | {c.latency_ms:.0f} ms | "
            f"{len(c.passed)}/{total} | {'pass' if c.ok else 'FAIL'} |"
        )

    failures = [c for c in cases if not c.ok]
    if failures:
        lines += ["", "## Failures", ""]
        for c in failures:
            lines.append(f"**`{c.id}`** — {c.question}")
            lines += [f"  - {f}" for f in c.failed]
            lines.append("")
    else:
        lines += ["", "All checks passed.", ""]

    lines += [
        "## What this does and does not prove",
        "",
        "It proves the assistant retrieves the expected artifact types, calls the",
        "exact-lookup tools it should, cites its sources, carries the disclaimer,",
        "refuses advice and guarantees, and abstains when a question falls outside",
        "the indexed material.",
        "",
        "It does not prove the explanations are good. Answer quality needs a human",
        "reading them, and the mock provider's wording is templated by design.",
        "",
    ]
    return "\n".join(lines)


def render_csv(cases: list[Case], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow([
            "id", "question", "intent", "sources", "latency_ms",
            "checks_passed", "checks_total", "result", "failed_checks",
        ])
        for c in cases:
            writer.writerow([
                c.id, c.question, c.intent, c.source_count, c.latency_ms,
                len(c.passed), len(c.passed) + len(c.failed),
                "pass" if c.ok else "fail", "; ".join(c.failed),
            ])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET)
    parser.add_argument("--format", choices=["markdown", "csv"], default="markdown")
    parser.add_argument("--out", type=Path, help="write the report to a file")
    parser.add_argument("--latency-budget", type=float, default=5000.0,
                        help="per-question budget in ms")
    parser.add_argument("--strict", action="store_true",
                        help="exit non-zero if any case fails")
    args = parser.parse_args()

    if not args.eval_set.exists():
        print(f"eval set not found: {args.eval_set}", file=sys.stderr)
        return 2

    artifact_source = use_fixtures_if_no_pipeline_output()

    import research
    from config import settings
    from research import ingest

    # always rebuild: the cached index may have been built against a different
    # artifact source, and stale vectors would make the scores meaningless
    ingest.build_index()
    health = research.health()

    specs = load_cases(args.eval_set)
    print(f"running {len(specs)} cases in "
          f"{settings.research_llm_provider} mode…", file=sys.stderr)

    cases = [evaluate_one(spec, args.latency_budget) for spec in specs]

    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "llm_provider": health["llm"]["provider"],
        "embedder": health["embedding"]["active"],
        "chunks": health["index"]["chunks"],
        "artifacts": health["index"]["artifacts"],
        "artifact_source": artifact_source,
    }

    if args.format == "csv":
        out = args.out or REPO_ROOT / "reports" / "research_ai_eval.csv"
        render_csv(cases, out)
        print(f"wrote {out}")
    else:
        report = render_markdown(cases, meta)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(report, encoding="utf-8")
            print(f"wrote {args.out}")
        else:
            print(report)

    failed = [c for c in cases if not c.ok]
    print(f"\n{len(cases) - len(failed)}/{len(cases)} cases passed", file=sys.stderr)
    return 1 if (failed and args.strict) else 0


if __name__ == "__main__":
    raise SystemExit(main())
