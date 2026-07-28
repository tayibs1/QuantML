"""
Find everything the research assistant is allowed to talk about.

Two sources feed the registry. The `corpus/` folder next to this file holds
hand-written explanatory documents that ship with the repo, so the assistant can
explain the methodology on a fresh clone before anything has been run. The rest
is discovered from `data/`, which is where the pipeline drops its output.

Anything the pipeline has not produced yet is simply absent. Nothing here raises
when a file is missing, because a cold checkout is a normal state and the
assistant is expected to say "no evidence for that" rather than fall over.

Numbers found in JSON artifacts are copied into `numeric` so the structured tools
can read exact values instead of parsing them back out of prose.
"""
from __future__ import annotations

import json
from pathlib import Path

from config import settings

from .types import Artifact, ArtifactType

CORPUS_DIR = Path(__file__).parent / "corpus"
REPO_ROOT = Path(__file__).resolve().parents[2]

# Docs worth answering from. Anything not listed stays out of the index.
REPO_DOCS = [
    ("README.md", "QuantML project README"),
    ("docs/BACKEND.md", "Backend architecture and API contract"),
    ("backend/README.md", "Backend overview"),
    ("ml/README.md", "ML pipeline overview"),
    ("data/README.md", "Data layout"),
]

# Each research study writes its own file; this maps them to a type and a title.
RESEARCH_STUDIES: dict[str, tuple[ArtifactType, str]] = {
    "drift.json": ("drift_report", "Feature drift report"),
    "confidence.json": ("calibration_report", "Confidence calibration study"),
    "ood.json": ("validation_report", "Out-of-distribution detection study"),
    "rolling_window.json": ("walk_forward_report", "Rolling-window robustness study"),
    "window_comparison.json": ("walk_forward_report", "Training-window comparison study"),
    "regime_models.json": ("validation_report", "Regime-conditional model study"),
    "online_learning.json": ("validation_report", "Online learning study"),
    "data_health.json": ("validation_report", "Data quality report"),
}


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        return None


def _rel(path: Path) -> str:
    """Repo-relative path, so citations point somewhere a reader can open."""
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _front_matter(text: str) -> tuple[dict, str]:
    """Split a leading `---` block off a markdown file.

    Corpus documents declare their own artifact_type this way, which beats
    guessing it from the filename.
    """
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    meta = {}
    for line in text[3:end].splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip()
    return meta, text[end + 4:].lstrip("\n")


# --- turning JSON artifacts into something readable and quotable ---------------

def _signal_text(s: dict, generated_at: str) -> str:
    drivers = ", ".join(s.get("drivers") or []) or "none recorded"
    return (
        f"Latest signal for {s['ticker']} ({s.get('company', s['ticker'])}), "
        f"sector {s.get('sector', 'Unknown')}, generated {generated_at}.\n"
        f"Signal: {s['signal']}. Confidence: {s.get('confidence')}%. "
        f"Expected 5-day return: {s.get('expectedReturn5d')}%. "
        f"Risk level: {s.get('risk')}. Model: {s.get('model')}.\n"
        f"Last price {s.get('price')}, 1-day change {s.get('change')}%.\n"
        f"Top drivers: {drivers}.\n"
        f"BUY/HOLD/AVOID are relative rankings within the scored universe, not "
        f"absolute price forecasts."
    )


def _shap_text(ticker: str, row: dict, as_of: str, model: str) -> str:
    lines = [
        f"Feature attribution for {ticker} as of {as_of}, model {model}.",
        f"Predicted signal {row['signal']} with {row.get('confidence')}% confidence. "
        f"Base value {row.get('baseValue')}.",
        "Drivers, largest first. 'supports' pushed towards the predicted label, "
        "'opposes' pushed against it:",
    ]
    for d in row.get("drivers", [])[:10]:
        lines.append(
            f"  {d['label']} ({d['key']}): {d['contribution']:+} — {d['direction']}, "
            f"feature value {d['featureValue']}"
        )
    return "\n".join(lines)


def _backtest_text(bt: dict) -> str:
    m = bt.get("metrics", {})
    c = bt.get("config", {})
    w = bt.get("window", {})
    return (
        f"Walk-forward backtest, net of modelled costs. "
        f"Window {w.get('start')} to {w.get('end')} over {w.get('rebalances')} rebalances.\n"
        f"Settings: {c.get('rebalance')} rebalance, top {c.get('top_n')} names, "
        f"{c.get('commission_bps')} bps commission plus {c.get('slippage_bps')} bps "
        f"slippage, model {c.get('model')}.\n"
        f"Strategy CAGR {m.get('cagr')}, total return {m.get('totalReturn')}, "
        f"Sharpe {m.get('sharpe')}, Sortino {m.get('sortino')}, "
        f"volatility {m.get('volatility')}, max drawdown {m.get('maxDrawdown')}.\n"
        f"Benchmark (buy-and-hold QQQ) total return {m.get('benchTotalReturn')}, "
        f"CAGR {m.get('benchCagr')}. Beta {m.get('beta')}, "
        f"correlation to benchmark {m.get('benchCorrelation')}.\n"
        f"Closed trades: {bt.get('tradeCount')}.\n"
        f"All figures are simulated fills, not live executions."
    )


def _model_card_text(m: dict) -> str:
    return (
        f"Model {m.get('name')} ({m.get('id')}), family {m.get('family')}, "
        f"status {m.get('status')}.\n"
        f"Trained on {m.get('trainingWindow')}, validated by {m.get('validation')}.\n"
        f"Out-of-sample metrics: AUC {m.get('auc')}, accuracy {m.get('accuracy')}, "
        f"Sharpe {m.get('sharpe')}, CAGR {m.get('cagr')}, "
        f"max drawdown {m.get('maxDrawdown')}.\n"
        f"Feature count {m.get('features')}. Drift status {m.get('drift')}. "
        f"Last trained {m.get('lastTrained')}. Experiment {m.get('experimentId')}.\n"
        f"With three balanced classes, chance accuracy is about 33% and chance AUC "
        f"is 0.50; only the margin above those is skill."
    )


def _training_meta_text(meta: dict) -> str:
    mt = meta.get("metrics", {})
    return (
        f"Training configuration for {meta.get('model_name')}.\n"
        f"Label method: {meta.get('label_method')} over a "
        f"{meta.get('horizon_days')}-day horizon.\n"
        f"Class mapping: {meta.get('class_to_signal')}.\n"
        f"Mean forward return by class: {meta.get('class_mean_fwd_ret')}.\n"
        f"Trained {meta.get('train_start')} to {meta.get('train_end')}, "
        f"fitted {meta.get('trained_at')}.\n"
        f"Out-of-sample metrics: {json.dumps(mt)}.\n"
        f"Features used: {', '.join(meta.get('feature_cols', []))}."
    )


def _flat_numbers(obj, prefix: str = "", out: dict | None = None, depth: int = 0) -> dict:
    """Pull every number out of a nested dict into flat dotted keys."""
    out = {} if out is None else out
    if depth > 3 or not isinstance(obj, dict):
        return out
    for k, v in obj.items():
        key = f"{prefix}{k}"
        if isinstance(v, bool):
            continue
        if isinstance(v, int | float):
            out[key] = float(v)
        elif isinstance(v, dict):
            _flat_numbers(v, f"{key}.", out, depth + 1)
    return out


# --- discovery ----------------------------------------------------------------

def _corpus_artifacts() -> list[Artifact]:
    """The hand-written explainers that ship with the repo."""
    artifacts = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _front_matter(raw)
        artifacts.append(
            Artifact(
                artifact_id=f"corpus:{path.stem}",
                artifact_type=meta.get("artifact_type", "documentation"),
                title=meta.get("title", path.stem.replace("_", " ").title()),
                text=body,
                source_path=_rel(path),
                model_version=meta.get("model_version") or None,
            )
        )
    return artifacts


def _signal_artifacts() -> list[Artifact]:
    payload = _read_json(settings.signals_dir / "latest.json")
    if not payload or not payload.get("signals"):
        return []
    generated = payload.get("generatedAt", "")
    path = _rel(settings.signals_dir / "latest.json")
    artifacts = []
    for s in payload["signals"]:
        artifacts.append(
            Artifact(
                artifact_id=f"signal:{s['ticker']}",
                artifact_type="latest_signal",
                title=f"{s['ticker']} latest signal",
                text=_signal_text(s, generated),
                source_path=path,
                ticker=s["ticker"],
                model_version=s.get("model"),
                created_at=generated,
                numeric={
                    "confidence": float(s.get("confidence", 0)),
                    "expectedReturn5d": float(s.get("expectedReturn5d", 0)),
                    "price": float(s.get("price", 0)),
                    "change": float(s.get("change", 0)),
                },
            )
        )
    # a universe-level roll-up, so "how many BUYs are there" has something to hit
    counts = {k: sum(1 for s in payload["signals"] if s["signal"] == k)
              for k in ("BUY", "HOLD", "AVOID")}
    artifacts.append(
        Artifact(
            artifact_id="signal:universe",
            artifact_type="signal_history",
            title="Universe signal distribution",
            text=(
                f"Latest scoring run generated {generated} covering "
                f"{payload.get('count')} names.\n"
                f"BUY {counts['BUY']}, HOLD {counts['HOLD']}, AVOID {counts['AVOID']}.\n"
                f"Labels are cross-sectional terciles, so the split is roughly even "
                f"by construction and a high BUY count is not a bullish market call."
            ),
            source_path=path,
            created_at=generated,
            numeric={f"count_{k.lower()}": float(v) for k, v in counts.items()},
        )
    )
    return artifacts


def _shap_artifacts() -> list[Artifact]:
    payload = _read_json(settings.data_dir / "research" / "shap" / "latest.json")
    if not payload or not payload.get("tickers"):
        return []
    path = _rel(settings.data_dir / "research" / "shap" / "latest.json")
    as_of = payload.get("asOf", "")
    model = payload.get("model", "")
    artifacts = []
    for ticker, row in payload["tickers"].items():
        numeric = {
            d["key"]: float(d["contribution"]) for d in row.get("drivers", [])[:10]
        }
        numeric["baseValue"] = float(row.get("baseValue", 0))
        artifacts.append(
            Artifact(
                artifact_id=f"shap:{ticker}",
                artifact_type="shap_summary",
                title=f"{ticker} feature attribution",
                text=_shap_text(ticker, row, as_of, model),
                source_path=path,
                ticker=ticker,
                model_version=model,
                created_at=payload.get("generatedAt"),
                date_range=as_of,
                numeric=numeric,
            )
        )
    return artifacts


def _model_artifacts() -> list[Artifact]:
    artifacts: list[Artifact] = []

    card = _read_json(settings.models_dir / "model_card.json")
    if card:
        path = _rel(settings.models_dir / "model_card.json")
        for m in card.get("models", []):
            artifacts.append(
                Artifact(
                    artifact_id=f"model_card:{m.get('id', m.get('name'))}",
                    artifact_type="model_card",
                    title=f"{m.get('name')} model card",
                    text=_model_card_text(m),
                    source_path=path,
                    model_version=m.get("name"),
                    run_id=m.get("experimentId"),
                    date_range=m.get("trainingWindow"),
                    created_at=m.get("lastTrained"),
                    numeric={
                        k: float(v) for k, v in m.items()
                        if isinstance(v, int | float) and not isinstance(v, bool)
                    },
                )
            )
        fi = card.get("featureImportance") or []
        if fi:
            ranked = "\n".join(
                f"  {i + 1}. {f['feature']} ({f.get('key', '')}): {f['importance']}"
                for i, f in enumerate(fi[:20])
            )
            artifacts.append(
                Artifact(
                    artifact_id="model_card:feature_importance",
                    artifact_type="model_card",
                    title="Global feature importance",
                    text=(
                        "Global feature importance across the whole training set, "
                        "measured by gain. This answers which features the model "
                        "relies on in general, which is a different question from "
                        "which features moved one specific prediction.\n" + ranked
                    ),
                    source_path=path,
                    numeric={f.get("key", f["feature"]): float(f["importance"]) for f in fi},
                )
            )

    meta = _read_json(settings.models_dir / "xgb_signal.meta.json")
    if meta:
        artifacts.append(
            Artifact(
                artifact_id="model_registry:training_meta",
                artifact_type="model_registry_entry",
                title="Training configuration and out-of-sample metrics",
                text=_training_meta_text(meta),
                source_path=_rel(settings.models_dir / "xgb_signal.meta.json"),
                model_version=meta.get("model_name"),
                date_range=f"{meta.get('train_start')} … {meta.get('train_end')}",
                created_at=meta.get("trained_at"),
                numeric=_flat_numbers(meta.get("metrics", {})),
            )
        )

    registry = _read_json(settings.models_dir / "registry.json")
    if registry and registry.get("versions"):
        lines = [
            f"  {v.get('id')}: promoted {v.get('promotedAt', 'unknown')}, "
            f"Sharpe {v.get('sharpe', 'n/a')}"
            for v in registry["versions"]
        ]
        artifacts.append(
            Artifact(
                artifact_id="model_registry:versions",
                artifact_type="model_registry_entry",
                title="Champion model history",
                text="Versioned champion history.\n" + "\n".join(lines),
                source_path=_rel(settings.models_dir / "registry.json"),
            )
        )
    return artifacts


def _backtest_artifacts() -> list[Artifact]:
    bt = _read_json(settings.data_dir / "backtests" / "latest.json")
    if not bt:
        return []
    path = _rel(settings.data_dir / "backtests" / "latest.json")
    w = bt.get("window", {})
    artifacts = [
        Artifact(
            artifact_id="backtest:latest",
            artifact_type="backtest_report",
            title="Latest walk-forward backtest",
            text=_backtest_text(bt),
            source_path=path,
            model_version=(bt.get("config") or {}).get("model"),
            date_range=f"{w.get('start')} … {w.get('end')}",
            created_at=bt.get("generatedAt"),
            numeric=_flat_numbers(bt.get("metrics", {})),
        )
    ]

    monthly = bt.get("monthlyReturns") or []
    if monthly:
        lines = [
            f"  {row['year']}: " + ", ".join(
                f"{v:+.1f}%" for v in row["months"] if v is not None
            )
            for row in monthly
        ]
        artifacts.append(
            Artifact(
                artifact_id="backtest:monthly_returns",
                artifact_type="backtest_report",
                title="Backtest monthly returns",
                text=(
                    "Monthly strategy returns from the walk-forward backtest, net of "
                    "modelled costs. Useful for seeing whether performance is steady "
                    "or driven by a few months.\n" + "\n".join(lines)
                ),
                source_path=path,
                created_at=bt.get("generatedAt"),
            )
        )
    return artifacts


def _study_artifacts() -> list[Artifact]:
    research = settings.data_dir / "research"
    artifacts = []
    for filename, (atype, title) in RESEARCH_STUDIES.items():
        payload = _read_json(research / filename)
        if not payload:
            continue
        artifacts.append(
            Artifact(
                artifact_id=f"study:{filename.replace('.json', '')}",
                artifact_type=atype,
                title=title,
                text=f"{title}.\n{json.dumps(payload, indent=2)[:6000]}",
                source_path=_rel(research / filename),
                numeric=_flat_numbers(payload),
            )
        )
    return artifacts


def _doc_artifacts() -> list[Artifact]:
    artifacts = []
    for rel, title in REPO_DOCS:
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (FileNotFoundError, OSError):
            continue
        _, body = _front_matter(text)
        artifacts.append(
            Artifact(
                artifact_id=f"doc:{rel.replace('/', '_').replace('.md', '')}",
                artifact_type="documentation",
                title=title,
                text=body,
                source_path=rel,
            )
        )
    return artifacts


def discover() -> list[Artifact]:
    """Every artifact currently available, corpus first then pipeline output."""
    artifacts: list[Artifact] = []
    for source in (
        _corpus_artifacts,
        _doc_artifacts,
        _signal_artifacts,
        _shap_artifacts,
        _model_artifacts,
        _backtest_artifacts,
        _study_artifacts,
    ):
        try:
            artifacts.extend(source())
        except (OSError, ValueError, KeyError, TypeError):
            # one unreadable artifact source shouldn't take the whole index down
            continue
    return artifacts


def by_id(artifacts: list[Artifact]) -> dict[str, Artifact]:
    return {a.artifact_id: a for a in artifacts}
