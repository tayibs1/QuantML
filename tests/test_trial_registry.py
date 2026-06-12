"""Trial registry log + the multiple-testing statistics (PSR / DSR).

The log tests use tmp_path so they never touch the real data/research/trials.jsonl.
The stats tests pin down the properties that make the deflated Sharpe meaningful:
it rises with track-record length and falls as you run more trials.
"""
from __future__ import annotations

import pytest

from ml.research.trial_registry import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    load_trials,
    log_trial,
    probabilistic_sharpe_ratio,
    summary,
)


def test_log_then_load_roundtrip(tmp_path):
    path = tmp_path / "trials.jsonl"
    rec = log_trial("backtest", {"rebalance": "Weekly"}, {"sharpe": 0.7}, path=path)
    loaded = load_trials(path)
    assert len(loaded) == 1
    assert loaded[0]["trial_id"] == rec["trial_id"]
    assert loaded[0]["metrics"]["sharpe"] == 0.7


def test_log_is_append_only(tmp_path):
    path = tmp_path / "trials.jsonl"
    for s in (0.3, 0.5, 0.7):
        log_trial("backtest", {"rebalance": "Weekly", "s": s}, {"sharpe": s}, path=path)
    assert len(load_trials(path)) == 3


def test_load_skips_corrupt_lines(tmp_path):
    path = tmp_path / "trials.jsonl"
    log_trial("backtest", {"a": 1}, {"sharpe": 0.4}, path=path)
    with path.open("a", encoding="utf-8") as f:
        f.write("this is not json\n")
    assert len(load_trials(path)) == 1


def test_summary_picks_the_best(tmp_path):
    path = tmp_path / "trials.jsonl"
    for s in (0.32, 0.70, 0.51):
        log_trial("backtest", {"s": s}, {"sharpe": s}, path=path)
    s = summary(path=path)
    assert s["numTrials"] == 3
    assert s["bestValue"] == pytest.approx(0.70)
    assert s["distinctConfigs"] == 3


def test_summary_empty(tmp_path):
    assert summary(path=tmp_path / "none.jsonl")["numTrials"] == 0


def test_psr_half_at_the_benchmark():
    # estimate sits exactly on the reference Sharpe -> coin flip
    assert probabilistic_sharpe_ratio(0.5, n_obs=100, sr_ref=0.5) == pytest.approx(0.5, abs=1e-6)


def test_psr_rises_with_sharpe_and_with_track_record():
    assert probabilistic_sharpe_ratio(0.5, 100) > probabilistic_sharpe_ratio(0.1, 100)
    assert probabilistic_sharpe_ratio(0.3, 500) > probabilistic_sharpe_ratio(0.3, 50)


def test_psr_bounded_unit_interval():
    for sr in (-1.0, 0.0, 0.5, 3.0):
        p = probabilistic_sharpe_ratio(sr, 200)
        assert 0.0 <= p <= 1.0


def test_expected_max_sharpe_grows_with_trials():
    assert expected_max_sharpe(50, 0.5) > expected_max_sharpe(5, 0.5)
    # degenerate inputs collapse to zero (no selection bias to correct)
    assert expected_max_sharpe(1, 0.5) == 0.0
    assert expected_max_sharpe(10, 0.0) == 0.0


def test_dsr_is_stricter_than_psr():
    # deflating against expected-max-Sharpe must never be more generous than
    # the plain PSR-against-zero for the same estimate
    sr, n_obs, n_trials, std = 0.7, 252, 20, 0.25
    dsr = deflated_sharpe_ratio(sr, n_obs, n_trials, std)
    psr0 = probabilistic_sharpe_ratio(sr, n_obs, sr_ref=0.0)
    assert dsr <= psr0
    assert 0.0 <= dsr <= 1.0


def test_dsr_falls_as_trials_pile_up():
    # the same result looks less special once you admit you tried more configs
    base = dict(sr=0.7, n_obs=252, trial_sharpe_std=0.25)
    assert deflated_sharpe_ratio(n_trials=5, **base) > deflated_sharpe_ratio(n_trials=200, **base)
