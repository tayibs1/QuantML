---
artifact_type: model_card
title: Model limitations and failure modes
model_version: XGBoost-v3
---

# Model limitations and failure modes

The honest list of what this model cannot do and where it breaks. Anyone deciding
how much to trust a signal should read this before the performance numbers.

## What the model can see

Price and volume history, and nothing else.

All 24 features are derived from daily open, high, low, close and volume. The model
has no access to company fundamentals, earnings figures, guidance, analyst
estimates, filings, news, or anything a human analyst would consider.

This is the single largest limitation and it bounds everything else. A company can
announce disastrous results and the model will only notice once the price and
volume react. It is a pattern reader over recent trading behaviour, and it should
be read as one.

## Specific failure modes

**Regime change.** The model learned relationships from 2019 onwards. When the
market's character shifts, those relationships can invert. Momentum strategies in
particular tend to fail hardest at turning points, which are exactly the moments
when being right matters most.

**Crowded conditions.** Widely followed signals get arbitraged away. An edge visible
in historical data may already be gone by the time it is traded.

**Event risk.** Earnings, regulatory decisions and takeover news dominate short-term
returns and are invisible to the model until after the fact.

**Correlated features.** Several features measure overlapping things. The four
momentum windows move together, and rel_strength_20 starts from the same
calculation as ret_20. Attribution gets split across correlated features, so no
single driver's value should be read as its standalone importance.

**Low base rate of skill.** The validated edge is small. Over short periods, results
will be dominated by luck rather than by whatever skill exists.

**Survivorship bias.** The universe is built from a current list of large NASDAQ
names. Companies that failed or were delisted are missing from history, so the
past looks kinder than it was.

## When a signal deserves less trust

The confidence is close to 33%. With three groups, that is the guessing floor, and
a reading near it means the model has no real opinion.

The drift report is flagging feature distributions that have moved away from
training data. The model is being asked about conditions it did not learn.

The out-of-distribution check flags the current day as unusual.

The calibration report shows the model is overconfident in the confidence band your
signal falls into.

An earnings release or other scheduled event is imminent. The model does not know
about it.

The name is Elevated risk and the position is small as a result. The risk engine
has already reduced its size, which is a signal in itself.

The supporting drivers are all correlated momentum features. That is one bet, not
several independent ones.

## What this system is not

It is not a trading system. It emits signals; live trading is disabled by design.

It is not financial advice, and it is not an assessment of any company's quality or
prospects.

It is not a forecast of price. The output is a relative ranking within a universe on
a 5-day horizon.

It has no risk management for an individual's circumstances. Position caps are
portfolio-level rules, not suitability judgements.
