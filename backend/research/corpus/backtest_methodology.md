---
artifact_type: backtest_report
title: Backtest methodology and cost model
model_version: XGBoost-v3
---

# Backtest methodology and cost model

How the simulated track record is produced, and why the costs matter so much.

Source: `backend/backtesting/`, `backend/services/backtest_service.py`.

## What is being simulated

The backtest replays history one rebalance at a time using only the out-of-sample
walk-forward predictions. At each rebalance it takes the model's signals, passes
them through the same risk engine that runs live, and holds the resulting book
until the next rebalance.

Two details make this a fair test rather than a flattering one.

First, the predictions are out-of-sample. At every historical date, the signal used
came from a model trained only on earlier data.

Second, signals go through the real risk engine rather than being traded directly.
The backtest measures the strategy that would actually run, including its position
caps and sizing rules, not an idealised version.

The benchmark is buy-and-hold QQQ, which is the honest comparison: it is what you
could have done instead with no model and no effort.

## The cost model

Trading is not free, and in a strategy that rebalances weekly the costs compound
into a large drag.

Two costs are charged, both in basis points, where one basis point is 0.01%.

**Commission** defaults to 5 bps. This stands in for broker fees.

**Slippage** defaults to 8 bps. This covers the gap between the price you see and
the price you get. Your own order moves the market against you, and the faster you
need to trade the worse it gets.

Together that is 13 bps per round trip, charged against the fraction of the
portfolio that actually changed hands at each rebalance. Holding a position from
one week to the next costs nothing; only the traded portion is charged.

## Why costs decide the outcome

This is the single most important thing to understand about the results.

A strategy holding 20 names and rebalancing weekly can turn over a large share of
the book every week. At 13 bps per round trip, that drag accumulates across a
year into a serious headwind that must be overcome before the first dollar of
profit.

The practical consequence is that a strategy can have genuine predictive skill and
still lose to the benchmark after costs. Gross returns and net returns can tell
opposite stories, and only the net number is real.

Any performance figure quoted from QuantML's backtest is net of these modelled
costs. The cost assumptions are adjustable in the dashboard, and moving the sliders
is the fastest way to see how much of the result depends on them.

## Reading the metrics

**CAGR** is the annualised growth rate, net of costs.

**Sharpe** is return per unit of volatility. Higher means a smoother path to the
same place. Below 1.0 is a bumpy ride.

**Sortino** is like Sharpe but only counts downside moves as risk, on the argument
that upside volatility is not something to be penalised for.

**Max drawdown** is the worst peak-to-trough fall. This is the number that decides
whether a strategy is survivable in practice, because it describes the loss you
would have had to sit through without abandoning it.

**Beta** and **benchmark correlation** show how much of the result is simply market
exposure. A strategy with high correlation to QQQ is mostly delivering the
benchmark with extra steps, and its returns should be judged against that.

## Limits

These are simulated fills, not real ones. No order was ever sent.

Costs are modelled with fixed rates rather than measured from actual executions.
Real slippage varies with order size, volatility and liquidity, and gets worse
exactly when the strategy most wants to trade.

The simulation assumes every intended trade fills at the modelled price. It does
not model partial fills, halted stocks, or the possibility that the price moved
before the order arrived.

The universe carries survivorship bias: it is built from a current list of large
NASDAQ names, so companies that collapsed or dropped out are absent from history.
