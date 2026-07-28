---
artifact_type: risk_report
title: Risk controls and position sizing
---

# Risk controls and position sizing

A signal is not a position. This layer decides whether to hold a name at all and
how much of it, under hard limits.

Source: `backend/portfolio/risk_engine.py`.

## Signals do not become trades on their own

The separation matters and it is deliberate:

    model predicts  ->  risk engine sizes  ->  execution adapter acts

The model only ever emits signals. It has no ability to create an order. Turning a
signal into a proposed position is the risk engine's job, and acting on a proposal
only happens inside the execution adapter. Live trading is disabled by a flag that
has to be switched on deliberately.

This is why the raw signal and the risk-adjusted position can disagree. A high
confidence BUY on a very volatile name can end up with a smaller position than a
moderate BUY on a calm one.

## How a position gets sized

**Only BUY names are considered.** The book is long-only. An AVOID signal results
in no position rather than a short.

**Raw weight starts as confidence multiplied by a volatility factor.** The factor
cuts size as risk rises: Low keeps 100% of the raw weight, Moderate 80%, High 60%,
Elevated 45%. So an Elevated-risk name needs far more model conviction to earn the
same position as a Low-risk one.

**At most 25 positions** are held, taking the highest-confidence names first.

**Weights are normalised** so the book targets 100% gross exposure.

**Per-name cap of 20%.** No single stock can exceed a fifth of the book regardless
of how confident the model is. This is the control that limits the damage from any
one prediction being wrong.

**Per-sector cap of 40%.** If a sector exceeds it, every position in that sector is
scaled back proportionally. Because the universe is NASDAQ-heavy, the model
frequently wants more technology exposure than this allows, and this cap binds
often.

## What these controls do and do not protect against

They limit concentration. If one position collapses, the per-name cap bounds the
loss. If one sector turns, the sector cap bounds it.

They do not protect against the market falling as a whole. The book is long-only
and targets full exposure, so a broad selloff hits it directly. The backtest's
maximum drawdown is the honest measure of that exposure.

They also do not protect against the model being systematically wrong. Position
caps limit the damage from one bad call, not from a model whose edge has quietly
stopped working. That risk is monitored through drift and calibration studies
rather than through position limits.

## Risk levels are volatility only

The Low, Moderate, High and Elevated labels rank each stock's recent 20-day
volatility against the rest of the universe. That is their entire content.

They do not include upcoming earnings dates, company-specific news, liquidity,
balance sheet health, or how crowded a trade has become. A stock can carry a Low
risk label and still be days from an event the system knows nothing about.
