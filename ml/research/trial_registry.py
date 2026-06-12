"""
Append-only log of every backtest/experiment trial.

Each backtest is a trial. Run fifty configs and report the best one and its
Sharpe is inflated by selection alone - the more you try, the higher the best
in-sample number you'd expect from luck. The fix (AFML ch.8, and the Deflated
Sharpe Ratio paper) is to write down every trial, then haircut the winner's
Sharpe by how many trials you ran and how spread out they were.

This file is the writing-down part (a JSONL log, one trial per line) plus the
stats for the haircut: Probabilistic and Deflated Sharpe.

A couple of decisions worth noting:
  - Append-only, one JSON object per line, never rewritten. Keeps the count of
    configs-tried honest.
  - Standard library only (no pandas/scipy) so it imports cleanly from either
    side, ML pipeline or API, without dragging heavy deps along.

    python -m ml.research.trial_registry        # print a summary of the log
"""
from __future__ import annotations

import hashlib
import json
import math
import uuid
from datetime import UTC, datetime
from pathlib import Path

# resolve the path ourselves (repo_root/data/research/trials.jsonl) so importing
# this module pulls in nothing else from the package
_REPO_ROOT = Path(__file__).resolve().parents[2]
TRIALS_PATH = _REPO_ROOT / "data" / "research" / "trials.jsonl"

_EULER_MASCHERONI = 0.5772156649015329


# --- the log itself ---
def _config_hash(config: dict) -> str:
    """Short stable hash of a config so repeat configs are easy to spot."""
    blob = json.dumps(config, sort_keys=True, default=str)
    return hashlib.sha1(blob.encode()).hexdigest()[:10]


def log_trial(
    kind: str,
    config: dict,
    metrics: dict,
    tags: list[str] | None = None,
    notes: str = "",
    path: Path = TRIALS_PATH,
) -> dict:
    """Append one trial and return the record we wrote.

    kind     "backtest", "training", etc.
    config   the settings that define the trial (rebalance, costs, ...)
    metrics  the headline results (sharpe, cagr, maxDrawdown, ...)
    """
    record = {
        "trial_id": uuid.uuid4().hex[:12],
        "timestamp": datetime.now(UTC).isoformat(),
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
    """Read every trial, skipping any line that won't parse."""
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
    """Roll the log up: how many trials, how many distinct configs, the best one."""
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


# --- selection-bias stats (the whole reason the log exists) ---
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
    """P(true Sharpe > sr_ref) given an estimate sr from n_obs observations.

    Factors in track-record length and the skew/kurtosis of returns: a short,
    fat-tailed record makes a high Sharpe a lot less convincing.
    """
    if n_obs < 2:
        return 0.0
    denom = math.sqrt(1 - skew * sr + (kurt - 1) / 4.0 * sr * sr)
    if denom <= 0:
        return 0.0
    z = (sr - sr_ref) * math.sqrt(n_obs - 1) / denom
    return _norm_cdf(z)


def expected_max_sharpe(n_trials: int, trial_sharpe_std: float) -> float:
    """Expected best Sharpe across n_trials independent no-skill strategies.

    Even with true Sharpe = 0 everywhere, the best of N trials comes out positive
    by chance. That's the bar a real strategy has to clear (AFML / DSR paper).
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
    """Probability the best-of-N strategy is actually skilful, not just lucky.

    Same as PSR but measured against the expected-max-Sharpe bar instead of zero.
    Near 1 means it survives the multiple-testing correction; around 0.5 or below
    means it's consistent with luck given how many trials were run.
    """
    sr_ref = expected_max_sharpe(n_trials, trial_sharpe_std)
    return probabilistic_sharpe_ratio(sr, n_obs, sr_ref=sr_ref, skew=skew, kurt=kurt)


def main() -> None:
    s = summary()
    print(f"Trial registry · {TRIALS_PATH.relative_to(_REPO_ROOT)}")
    if not s["numTrials"]:
        print("  (empty - run a backtest to record the first trial)")
        return
    print(f"  trials          {s['numTrials']}  ({s['distinctConfigs']} distinct configs · {s['kinds']})")
    print(f"  best {s['metric']:<10} {s['bestValue']:.3f}   config={s['best']['config']}")
    # only worth contextualising the best one if the trials actually spread out
    if s["numTrials"] >= 2 and s["trialMetricStd"] > 0:
        bm = s["best"]["metrics"]
        n_obs = int(bm.get("nObs") or bm.get("rebalances") or 252)
        dsr = deflated_sharpe_ratio(s["bestValue"], n_obs, s["numTrials"], s["trialMetricStd"])
        thr = expected_max_sharpe(s["numTrials"], s["trialMetricStd"])
        print(f"  selection check expected-max Sharpe under null ≈ {thr:.3f} across {s['numTrials']} trials")
        print(f"  deflated SR     {dsr:.3f}  (P[best is skilful, not lucky])")


if __name__ == "__main__":
    main()
