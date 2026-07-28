---
artifact_type: validation_report
title: Validation methodology
model_version: XGBoost-v3
---

# Validation methodology

How QuantML checks whether the model actually works, and what those checks can and
cannot prove.

Source: `ml/training/walk_forward.py`, `ml/validation.py`.

## Walk-forward, not a random split

The obvious way to test a model is to hide a random slice of the data and check
predictions against it. For market data that method is broken, and it is broken in
a way that flatters the model badly.

The problem is that a random split lets the model train on next Tuesday while being
tested on this Monday. Prices are connected across time, so training on the future
leaks the answer backwards. Models validated that way look excellent and then fail
the moment they meet genuinely unseen data.

QuantML instead uses expanding-window walk-forward validation across 6 folds. The
data is ordered by date. The model trains on everything up to a cutoff, is tested
only on dates after that cutoff, then the cutoff moves forward and the process
repeats with a larger training window.

Every prediction used to score the model was therefore made by a version of the
model that had never seen that date. This is the honest way to test, and it
reliably produces worse-looking numbers than a random split. Lower numbers here are
a sign the test is working, not a sign the model is bad.

## What the reported metrics mean

Metrics are aggregated across all out-of-sample fold predictions.

**Accuracy** is the share of predictions where the model picked the right one of
the three groups. Because the groups are equal thirds by construction, guessing
scores about 33%. Only the margin above 33% is real skill.

**AUC** measures ranking quality: given a good stock and a bad one, how often does
the model rank them the right way round. 0.50 is a coin flip. Anything above that
is signal. In this domain even small edges above 0.50 can be tradeable, which is
also why they are easy to imagine when they are not there.

**BUY hit rate** is how often names labelled BUY actually landed in the top group.

**Sharpe** and **CAGR** come from the backtest rather than the classifier, and are
described in the backtest methodology document.

## Honest expectations

Daily equity prediction is close to the hardest setting there is. Any single model
here should be expected to have a small edge at best. A validated AUC in the low
0.50s is a normal, credible result for this problem.

If a model in this domain reports accuracy far above chance, or an AUC near 0.70,
the first thing to suspect is a leak in the data pipeline rather than a genuine
discovery.

## The supporting studies

Walk-forward alone does not answer every question, so `ml/research/` runs several
additional checks. Each writes its own artifact under `data/research/`.

**Rolling window** re-trains across different time windows to see whether
performance holds up or depends on one lucky period.

**Window comparison** sweeps the training window length to test how sensitive the
result is to that choice.

**Regime models** splits history into market conditions and checks where the model
works and where it does not.

**Out-of-distribution detection** flags days where current data looks unlike
anything in training. Predictions on those days deserve less trust.

**Confidence calibration** checks whether stated confidence matches reality. If the
model says 70% confident, it should be right about 70% of the time. Models are
frequently overconfident, and this is the study that catches it.

**Online learning** tests whether updating the model continuously beats retraining
on a fixed schedule.

**Drift** compares the distribution of live feature values against training values.
When they diverge, the model is being asked about a world it was not trained on.

## Limits of this validation

Walk-forward removes lookahead leakage from the time dimension. It does not remove
every problem.

The universe is a current list of large NASDAQ names, so companies that failed or
dropped out are not represented. That is survivorship bias and it flatters results.

Every model that has been evaluated was evaluated on the same history. The more
variants are tested against it, the more likely a good result is a coincidence of
that particular history rather than a real edge.

Backtest costs are modelled with fixed assumptions rather than measured fills, so
the cost of trading is estimated rather than observed.
