"""
Research trial registry — an append-only experiment log.

Every backtest you run is a *trial*. If you try fifty configurations and report
the best, its Sharpe is biased upward purely by selection — the more trials, the
higher the best in-sample result you expect by luck alone. The defence (López de
Prado, AFML §8 and *The Deflated Sharpe Ratio*) is to (a) record every trial and
(b) deflate the winner's Sharpe by the number of trials and their dispersion.

This module is the (a) — a tamper-evident, append-only JSONL log — plus the
statistics for (b): the Probabilistic and Deflated Sharpe Ratios.

Design notes
------------
- **Append-only**: each trial is one JSON object on its own line. We never rewrite
  history, so the log is a faithful record of how many configurations were tried.
- **Self-contained**: pure standard library (no pandas/scipy), so it is safe to
  import from anywhere — the ML pipeline or the API backend — with no heavy deps.

    python -m ml.research.trial_registry        # print a summary of the log
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Self-contained path resolution (repo_root/data/research/trials.jsonl) so this
# module has zero import-time dependencies on the rest of the package.
_REPO_ROOT = Path(__file__).resolve().parents[2]
TRIALS_PATH = _REPO_ROOT / "data" / "research" / "trials.jsonl"

_EULER_MASCHERONI = 0.5772156649015329


# --------------------------------------------------------------------------- #
# Append-only log                                                              #
# --------------------------------------------------------------------------- #
def _config_hash(config: dict) -> str:
    """Stable short hash of a config, so repeated configurations are visible."""
    blob = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def log_trial(
    kind: str,
    config: dict,
    metrics: dict,
    tags: Optional[list[str]] = None,
    notes: str = "",
    path: Path = TRIALS_PATH,
) -> dict:
    """Append one trial to the registry and return the written record.

    `kind`    — e.g. "backtest", "training".
    `config`  — the settings that define the trial (rebalance, costs, …).
    `metrics` — the headline results (sharpe, cagr, maxDrawdown, …).
    """
    record = {
        "trial_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
        "config_hash": _config_hash(config),
        "config": config,
        "metrics": metrics,
        "tags": tags or [],
        "notes": notes,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, default=str) + "\n")
    return record


def load_trials(path: Path = TRIALS_PATH) -> list[dict]:
    """Read every trial from the log (skipping any corrupt lines)."""
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def summary(metric: str = "sharpe", path: Path = TRIALS_PATH) -> dict:
    """Aggregate the log: trial count, distinct configs, and the best trial."""
    trials = load_trials(path)
    if not trials:
        return {"numTrials": 0, "distinctConfigs": 0, "best": None}

    scored = [(t["metrics"].get(metric), t) for t in trials if t["metrics"].get(metric) is not None]
    best = max(scored, key=lambda x: x[0])[1] if scored else None
    sharpes = [s for s, _ in scored]
    return {
        "numTrials": len(trials),
        "distinctConfigs": len({t.get("config_hash") for t in trials}),
        "kinds": sorted({t.get("kind", "?") for t in trials}),
        "metric": metric,
        "bestValue": max(sharpes) if sharpes else None,
        "best": {"trial_id": best["trial_id"], "config": best["config"], "metrics": best["metrics"]} if best else None,
        "trialMetricStd": _std(sharpes) if len(sharpes) > 1 else 0.0,
    }


# --------------------------------------------------------------------------- #
# Selection-bias statistics (the reason the log exists)                        #
# --------------------------------------------------------------------------- #
def _std(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_ppf(p: float) -> float:
    """Inverse standard-normal CDF (Acklam's rational approximation)."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    r = q * q
    return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)


def probabilistic_sharpe_ratio(
    sr: float, n_obs: int, sr_ref: float = 0.0, skew: float = 0.0, kurt: float = 3.0
) -> float:
    """P(true Sharpe > sr_ref) given the estimate `sr` from `n_obs` observations.

    Accounts for track-record length and the non-normality (skew/kurtosis) of
    returns — a short, fat-tailed record makes a high Sharpe far less certain.
    """
    if n_obs < 2:
        return 0.0
    denom = math.sqrt(1 - skew * sr + (kurt - 1) / 4.0 * sr * sr)
    if denom <= 0:
        return 0.0
    z = (sr - sr_ref) * math.sqrt(n_obs - 1) / denom
    return _norm_cdf(z)


def expected_max_sharpe(n_trials: int, trial_sharpe_std: float) -> float:
    """Expected maximum Sharpe across `n_trials` independent null strategies.

    Under the null (true Sharpe = 0), the best of N trials is non-zero purely by
    chance; this is the threshold a real strategy must clear (AFML, DSR paper).
    """
    if n_trials < 2 or trial_sharpe_std <= 0:
        return 0.0
    e = math.e
    return trial_sharpe_std * (
        (1 - _EULER_MASCHERONI) * _norm_ppf(1 - 1.0 / n_trials)
        + _EULER_MASCHERONI * _norm_ppf(1 - 1.0 / (n_trials * e))
    )


def deflated_sharpe_ratio(
    sr: float,
    n_obs: int,
    n_trials: int,
    trial_sharpe_std: float,
    skew: float = 0.0,
    kurt: float = 3.0,
) -> float:
    """Probability the best-of-N strategy is genuinely skilful, not lucky.

    DSR = PSR evaluated against the expected-maximum-Sharpe benchmark instead of
    zero. A DSR near 1 survives the multiple-testing correction; near 0.5 or below
    means the result is consistent with luck across the trials run.
    """
    sr_ref = expected_max_sharpe(n_trials, trial_sharpe_std)
    return probabilistic_sharpe_ratio(sr, n_obs, sr_ref=sr_ref, skew=skew, kurt=kurt)


def main() -> None:
    s = summary()
    print(f"Trial registry · {TRIALS_PATH.relative_to(_REPO_ROOT)}")
    if not s["numTrials"]:
        print("  (empty — run a backtest to record the first trial)")
        return
    print(f"  trials          {s['numTrials']}  ({s['distinctConfigs']} distinct configs · {s['kinds']})")
    print(f"  best {s['metric']:<10} {s['bestValue']:.3f}   config={s['best']['config']}")
    # If we have a spread of trial Sharpes, contextualise the best one.
    if s["numTrials"] >= 2 and s["trialMetricStd"] > 0:
        bm = s["best"]["metrics"]
        n_obs = int(bm.get("nObs") or bm.get("rebalances") or 252)
        dsr = deflated_sharpe_ratio(s["bestValue"], n_obs, s["numTrials"], s["trialMetricStd"])
        thr = expected_max_sharpe(s["numTrials"], s["trialMetricStd"])
        print(f"  selection check expected-max Sharpe under null ≈ {thr:.3f} across {s['numTrials']} trials")
        print(f"  deflated SR     {dsr:.3f}  (P[best is skilful, not lucky])")


if __name__ == "__main__":
    main()
