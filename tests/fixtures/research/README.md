# Research AI fixture artifacts

A miniature version of what the pipeline writes to `data/`: three tickers, one
model, one backtest.

`data/` is gitignored, so it doesn't exist on a fresh clone or in CI. These files
stand in for it, which means the tests and the evaluation harness produce the
same numbers on every machine.

Chosen so the interesting cases are all reachable:

- **NVDA** is a HOLD at 36.5% confidence — just above the 33% level that means no
  opinion with three classes. It's what the false-premise test asks about ("why
  did NVDA get a BUY"), and what the near-chance confidence warning triggers on.
- **AMD** is a BUY at 71% with both supporting and opposing drivers, and has
  closed trades in the backtest ledger.
- **INTC** is an AVOID, so the long-only "no position rather than a short" path
  gets exercised.

The backtest numbers mirror the real ones: the strategy underperforms
buy-and-hold QQQ after costs. Fixtures that quietly flatter the model would let a
regression through.

Point the config at this directory to use them:

```python
settings.data_dir  ->  tests/fixtures/research
```

`scripts/evaluate_research_ai.py` does this automatically when `data/` has no
signals, and says which source it used in its report.
