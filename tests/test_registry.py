"""Model registry: versioning + the Deflated-Sharpe promotion gate."""
from __future__ import annotations

from ml.registry import champion, promote, register_version, rollback, versions


def _model(name: str = "XGBoost-v3", sharpe: float = 1.19) -> dict:
    return {
        "name": name, "family": "Gradient Boosting", "sharpe": sharpe, "auc": 0.54,
        "cagr": 31.2, "maxDrawdown": -29.3, "accuracy": 0.366,
        "trainingWindow": "2018 … 2026", "features": 24,
    }


def test_register_assigns_incrementing_versions_and_gate_flag(tmp_path):
    p = tmp_path / "registry.json"
    a = register_version(_model("A"), dsr=0.95, path=p)
    b = register_version(_model("B"), dsr=0.40, path=p)
    assert (a["version"], b["version"]) == ("v1", "v2")
    assert a["gatePassed"] is True and b["gatePassed"] is False
    assert a["status"] == "candidate"
    assert a["metrics"]["sharpe"] == 1.19


def test_promote_passes_when_dsr_clears_gate(tmp_path):
    p = tmp_path / "registry.json"
    a = register_version(_model("A"), dsr=0.96, path=p)
    res = promote(a["id"], path=p)
    assert res["promoted"] is True
    champ = champion(p)
    assert champ["id"] == a["id"] and champ["status"] == "champion"


def test_promote_blocked_below_gate(tmp_path):
    p = tmp_path / "registry.json"
    a = register_version(_model("A"), dsr=0.50, path=p)
    res = promote(a["id"], path=p)
    assert res["promoted"] is False
    assert "below gate" in res["reason"]
    assert champion(p) is None  # nothing got promoted


def test_rollback_restores_previous_champion(tmp_path):
    p = tmp_path / "registry.json"
    a = register_version(_model("A"), dsr=0.96, path=p)
    promote(a["id"], path=p)
    b = register_version(_model("B"), dsr=0.97, path=p)
    promote(b["id"], path=p)
    assert champion(p)["id"] == b["id"]

    res = rollback(path=p)
    assert res["rolledBack"] is True
    assert champion(p)["id"] == a["id"]
    status = {v["id"]: v["status"] for v in versions(p)}
    assert status[a["id"]] == "champion" and status[b["id"]] == "archived"
