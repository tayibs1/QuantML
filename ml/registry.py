"""
Model registry — versioned champions with a Deflated-Sharpe promotion gate.

The trial registry (ml.research.trial_registry) logs every experiment. This sits one
level above it and tracks which trained model is the *champion*, keeping an auditable
history of promotions and rollbacks.

The point worth making: a model is only allowed to become champion if it clears the
Deflated Sharpe Ratio gate — the same multiple-testing correction that guards the
research, enforced here at promotion time. A lucky in-sample run can't quietly take
over, and rolling back to the previous champion is one command.

    python -m ml.registry                 # show the registry
    python -m ml.registry --register      # snapshot the current model_card as a version
    python -m ml.registry --promote <id>  # promote (DSR-gated); archives the old champion
    python -m ml.registry --rollback      # revert to the previous champion

Stdlib only, so the backend can read the artifact without importing the ML stack.
"""
from __future__ import annotations

import argparse
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ml import paths

# probability the champion is skilful (not lucky) required to promote
DSR_GATE = 0.90

_METRIC_KEYS = ("sharpe", "auc", "cagr", "maxDrawdown", "accuracy")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def load_registry(path: Path = paths.REGISTRY_PATH) -> dict:
    """Read the registry, or an empty one if it doesn't exist yet."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"versions": [], "championId": None}


def _save(reg: dict, path: Path = paths.REGISTRY_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(reg, indent=2), encoding="utf-8")


def versions(path: Path = paths.REGISTRY_PATH) -> list[dict]:
    return load_registry(path)["versions"]


def champion(path: Path = paths.REGISTRY_PATH) -> dict | None:
    reg = load_registry(path)
    return next((v for v in reg["versions"] if v["id"] == reg["championId"]), None)


def register_version(
    model: dict, dsr: float | None = None, path: Path = paths.REGISTRY_PATH
) -> dict:
    """Append a new candidate version built from a model_card model entry."""
    reg = load_registry(path)
    entry = {
        "id": uuid.uuid4().hex[:10],
        "version": f"v{len(reg['versions']) + 1}",
        "name": model.get("name", "model"),
        "family": model.get("family", ""),
        "status": "candidate",
        "metrics": {k: model.get(k) for k in _METRIC_KEYS if model.get(k) is not None},
        "trainWindow": model.get("trainingWindow", ""),
        "features": model.get("features"),
        "dsr": round(dsr, 4) if dsr is not None else None,
        "gatePassed": bool(dsr is not None and dsr >= DSR_GATE),
        "registeredAt": _now(),
        "promotedAt": None,
    }
    reg["versions"].append(entry)
    _save(reg, path)
    return entry


def promote(
    version_id: str, dsr_threshold: float = DSR_GATE, path: Path = paths.REGISTRY_PATH
) -> dict:
    """Promote a version to champion, but only if it clears the DSR gate."""
    reg = load_registry(path)
    target = next((v for v in reg["versions"] if v["id"] == version_id), None)
    if target is None:
        return {"promoted": False, "reason": f"no version {version_id}"}

    dsr = target.get("dsr")
    if dsr is None or dsr < dsr_threshold:
        return {
            "promoted": False,
            "reason": f"DSR {dsr} below gate {dsr_threshold} — selection bias not ruled out",
        }

    for v in reg["versions"]:
        if v["status"] == "champion":
            v["status"] = "archived"
    target["status"] = "champion"
    target["promotedAt"] = _now()
    reg["championId"] = target["id"]
    _save(reg, path)
    return {"promoted": True, "championId": target["id"], "version": target["version"]}


def rollback(path: Path = paths.REGISTRY_PATH) -> dict:
    """Revert to the most recently archived champion (undo the last promotion)."""
    reg = load_registry(path)
    current = next((v for v in reg["versions"] if v["id"] == reg["championId"]), None)
    archived = [v for v in reg["versions"] if v["status"] == "archived" and v.get("promotedAt")]
    if not archived:
        return {"rolledBack": False, "reason": "no prior champion to roll back to"}

    previous = max(archived, key=lambda v: v["promotedAt"])
    if current:
        current["status"] = "archived"
    previous["status"] = "champion"
    previous["promotedAt"] = _now()
    reg["championId"] = previous["id"]
    _save(reg, path)
    return {"rolledBack": True, "championId": previous["id"], "version": previous["version"]}


def _dsr_for(metrics: dict) -> float | None:
    """Deflated Sharpe of the model's Sharpe given how many trials we've run."""
    from ml.research.trial_registry import deflated_sharpe_ratio, summary

    sr = metrics.get("sharpe")
    if sr is None:
        return None
    s = summary()
    n_trials = max(s.get("numTrials", 1), 1)
    trial_std = s.get("trialMetricStd") or 0.0
    n_obs = int(metrics.get("rebalances") or 252)
    if n_trials < 2 or trial_std <= 0:
        # not enough trials to deflate; fall back to undeflated PSR vs zero
        from ml.research.trial_registry import probabilistic_sharpe_ratio
        return round(probabilistic_sharpe_ratio(sr, n_obs), 4)
    return round(deflated_sharpe_ratio(sr, n_obs, n_trials, trial_std), 4)


def _register_from_card() -> dict:
    card = json.loads(paths.MODEL_CARD_PATH.read_text(encoding="utf-8"))
    model = (card.get("models") or [{}])[0]
    return register_version(model, dsr=_dsr_for(model))


def _print_registry() -> None:
    reg = load_registry()
    if not reg["versions"]:
        print("Model registry empty — run `python -m ml.registry --register` first.")
        return
    print(f"Model registry · {paths.REGISTRY_PATH.relative_to(paths.REPO_ROOT)}")
    for v in reg["versions"]:
        mark = "★" if v["id"] == reg["championId"] else " "
        sr = v["metrics"].get("sharpe", "—")
        gate = "gate✓" if v["gatePassed"] else "gate✗"
        print(f"  {mark} {v['version']:<4} {v['name']:<16} sharpe={sr:<5} "
              f"DSR={v['dsr']}  {gate}  {v['status']}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Model registry with a DSR promotion gate.")
    ap.add_argument("--register", action="store_true", help="snapshot the current model_card")
    ap.add_argument("--promote", metavar="ID", help="promote a version id to champion")
    ap.add_argument("--rollback", action="store_true", help="revert to the previous champion")
    args = ap.parse_args()

    if args.register:
        entry = _register_from_card()
        print(f"Registered {entry['version']} ({entry['id']})  DSR={entry['dsr']}  "
              f"gate {'passed' if entry['gatePassed'] else 'NOT passed'}")
    elif args.promote:
        print(promote(args.promote))
    elif args.rollback:
        print(rollback())
    else:
        _print_registry()


if __name__ == "__main__":
    main()
