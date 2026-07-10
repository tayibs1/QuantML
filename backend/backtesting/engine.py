
"""
Walk-Forward Backtest Engine

Tests how the QuantML strategy would have performed over time using only the
information that was available at each point in the past.

The goal is to make the backtest as close as possible to how the live system
actually works.

A few things keep the results realistic:

1. No future data is used.
   The model is trained on past data and then tested on the next unseen period.
   This process is repeated as time moves forward.

2. The same portfolio and risk logic is used as the live system.
   Predictions are passed through ``portfolio.propose_orders``, so the backtest
   follows the same position-sizing and risk rules as the live API.

3. Trading costs are included.
   Commission and slippage are deducted whenever the portfolio is rebalanced.
   This means returns, drawdown, and Sharpe ratio are all shown after costs.

4. Results are compared with QQQ.
   The strategy is measured against simply buying and holding QQQ over the same
   period.

The process is split into two parts:

    generate_oos_predictions()
        The slower step. It repeatedly trains the model using past data and
        saves the predictions to a parquet file. This usually only needs to be
        run when the model or data changes.

    simulate(oos, ...)
        The faster step. It uses the saved predictions to run the backtest.
        This can be repeated with different trading costs or rebalance settings
        without training the model again.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from config import REPO_ROOT, settings
from portfolio import RiskParams, propose_orders

from . import costs as cost_model
from . import metrics as M

# artifacts sit under data/ with everything else (gitignored)
BACKTEST_DIR = settings.data_dir / "backtests"
OOS_CACHE = BACKTEST_DIR / "oos_predictions.parquet"
RESULT_CACHE = BACKTEST_DIR / "latest.json"

BASE_CAPITAL = 1_000_000.0
_REBALANCE_DAYS = {"Daily": 1, "Weekly": 5, "Monthly": 21}
_CLASS_BUY = 2  # XGBoost class index for BUY (see ml/training)


@dataclass(frozen=True)
class BacktestConfig:
    rebalance: str = "Weekly"          # Daily | Weekly | Monthly
    top_n: int = 20                    # max names in the book
    commission_bps: float = 5.0
    slippage_bps: float = 8.0
    model: str = "XGBoost-v3"

    @property
    def rebalance_days(self) -> int:
        return _REBALANCE_DAYS.get(self.rebalance, 5)

    @property
    def periods_per_year(self) -> float:
        return 252.0 / self.rebalance_days


def _risk_bucket(vol_z: float) -> str:
    """Map a cross-sectional realized-vol z-score to the risk-engine's buckets."""
    if vol_z < -0.5:
        return "Low"
    if vol_z < 0.5:
        return "Moderate"
    if vol_z < 1.5:
        return "High"
    return "Elevated"


# --- stage 1: walk-forward OOS predictions (slow, reuses the ML training path) ---
def generate_oos_predictions(force: bool = False) -> pd.DataFrame:
    """Return [date, ticker, pred, p_buy, fwd_ret_5, vol_z, sector], cached.

    Goes through ml.training.walk_forward, so the predictions come out of the
    same validated, no-look-ahead procedure that produced the model metrics.
    """
    if OOS_CACHE.exists() and not force:
        return pd.read_parquet(OOS_CACHE)

    # lazy import - xgboost/sklearn are only needed here, in the slow offline
    # step, so the API never pays for importing them
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    from ml import paths as ml_paths
    from ml.features.build import FEATURE_COLS
    from ml.training.walk_forward import make_labels, walk_forward
    from ml.universe import sector as sector_of

    feats = pd.read_parquet(ml_paths.FEATURES_PATH)
    labelled = make_labels(feats)
    oos = walk_forward(labelled)  # [date, ticker, fwd_ret_5, label, pred, p_*]

    # carry the vol proxy and sector along on the predictions so simulate() can
    # run without the feature frame or the ml package in scope
    vol = feats[["date", "ticker", "vol_20"]]
    oos = oos.merge(vol, on=["date", "ticker"], how="left")
    oos["vol_z"] = oos["vol_20"].fillna(0.0)
    oos["sector"] = oos["ticker"].map(sector_of)
    oos = oos[["date", "ticker", "pred", "p_buy", "fwd_ret_5", "vol_z", "sector"]]

    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    oos.to_parquet(OOS_CACHE, index=False)
    _ = FEATURE_COLS  # touch it so a broken feature contract fails loudly here
    return oos


# --- stage 2: portfolio simulation (fast, pure pandas + the live risk engine) ---
def _book_at(rows: pd.DataFrame, cfg: BacktestConfig) -> dict[str, float]:
    """Build the long-only book for one rebalance through the live risk engine."""
    sigs = [
        {
            "ticker": r.ticker,
            "signal": "BUY" if int(r.pred) == _CLASS_BUY else ("HOLD" if int(r.pred) == 1 else "AVOID"),
            "confidence": float(r.p_buy) * 100.0,
            "risk": _risk_bucket(float(r.vol_z)),
            "sector": r.sector if isinstance(r.sector, str) else "Unknown",
        }
        for r in rows.itertuples(index=False)
    ]
    result = propose_orders(sigs, RiskParams(max_positions=cfg.top_n))
    return {o.ticker: o.target_weight for o in result["orders"]}


def simulate(
    oos: pd.DataFrame,
    close: dict,            # {date -> {ticker -> close}}
    bench: dict,            # {date -> close}
    cfg: BacktestConfig,
) -> dict:
    """Run the daily/weekly/monthly rebalance loop and assemble the result."""
    dates = sorted(oos["date"].unique())
    step = cfg.rebalance_days
    rebal = dates[::step]
    if len(rebal) < 3:
        raise ValueError("Not enough out-of-sample dates to backtest.")

    by_date = {d: g for d, g in oos.groupby("date")}
    cm = cost_model.CostModel(cfg.commission_bps, cfg.slippage_bps)

    nav_s = nav_b = 100.0
    peak = 100.0
    equity = [{"date": pd.Timestamp(rebal[0]).date().isoformat(),
               "strategy": 100.0, "benchmark": 100.0, "drawdown": 0.0}]
    period_returns: list[float] = []
    bench_returns: list[float] = []
    turnovers: list[float] = []

    open_pos: dict[str, dict] = {}
    trades: list[dict] = []
    seq = 0
    prev_book: dict[str, float] = {}

    for k in range(len(rebal) - 1):
        d0, d1 = rebal[k], rebal[k + 1]
        book = _book_at(by_date[d0], cfg) if d0 in by_date else {}

        # --- realised strategy return over [d0, d1], net of trading costs ---
        px0, px1 = close.get(d0, {}), close.get(d1, {})
        gross = 0.0
        for t, w in book.items():
            p0, p1 = px0.get(t), px1.get(t)
            if p0 and p1 and p0 > 0:
                gross += w * (p1 / p0 - 1.0)
        tn = cost_model.turnover(prev_book, book)
        net = gross - cm.cost_of_trading(tn)
        turnovers.append(tn)
        period_returns.append(net)

        # --- benchmark (buy-and-hold QQQ) over the same window ---
        b0, b1 = bench.get(d0), bench.get(d1)
        br = (b1 / b0 - 1.0) if (b0 and b1 and b0 > 0) else 0.0
        bench_returns.append(br)

        nav_s *= 1.0 + net
        nav_b *= 1.0 + br
        peak = max(peak, nav_s)
        equity.append({
            "date": pd.Timestamp(d1).date().isoformat(),
            "strategy": round(nav_s, 2),
            "benchmark": round(nav_b, 2),
            "drawdown": round((nav_s / peak - 1.0) * 100.0, 2),
        })

        # --- trade ledger: detect entries/exits vs the previous book ---
        for t in book:
            if t not in open_pos and px0.get(t):
                open_pos[t] = {"date": d0, "price": px0[t], "weight": book[t]}
        for t in list(open_pos):
            if t not in book:
                seq += 1
                trades.append(_close_trade(seq, t, open_pos.pop(t), d0, px0.get(t)))
        prev_book = book

    # Close anything still held at the final rebalance date.
    last = rebal[-1]
    for t in list(open_pos):
        seq += 1
        trades.append(_close_trade(seq, t, open_pos.pop(t), last, close.get(last, {}).get(t)))

    trades = [t for t in trades if t is not None]
    trades.sort(key=lambda x: x["date"], reverse=True)

    perf = M.performance_metrics(period_returns, [e["strategy"] for e in equity], bench_returns, cfg.periods_per_year)
    tstats = M.trade_stats(trades)
    perf["turnover"] = M.annualised_turnover(turnovers, cfg.periods_per_year)
    perf.update(tstats)

    return {
        "source": "live",
        "config": asdict(cfg),
        "window": {"start": equity[0]["date"], "end": equity[-1]["date"], "rebalances": len(rebal)},
        "metrics": perf,
        "summaryCards": _summary_cards(perf),
        "equity": equity,
        "trades": trades[:40],
        "tradeCount": len(trades),
        "monthlyReturns": _monthly_returns(equity, period_returns, rebal),
    }


def _close_trade(seq: int, ticker: str, pos: dict, exit_date, exit_price) -> dict | None:
    entry_price, entry_date, w = pos["price"], pos["date"], pos["weight"]
    if not exit_price or not entry_price or entry_price <= 0:
        return None
    ret = exit_price / entry_price - 1.0
    shares = w * BASE_CAPITAL / entry_price
    hold = (pd.Timestamp(exit_date) - pd.Timestamp(entry_date)).days
    return {
        "id": f"T-{1000 + seq}",
        "date": pd.Timestamp(exit_date).date().isoformat(),
        "ticker": ticker,
        "side": "LONG",
        "entry": round(float(entry_price), 2),
        "exit": round(float(exit_price), 2),
        "pnl": round((exit_price - entry_price) * shares),
        "ret": round(ret * 100.0, 2),
        "hold": int(max(hold, 1)),
    }


def _monthly_returns(equity: list[dict], period_returns: list[float], rebal: list) -> list[dict]:
    """Compound the period returns into a year-by-month grid for the heatmap."""
    df = pd.DataFrame({
        "date": pd.to_datetime([pd.Timestamp(d) for d in rebal[1:]]),
        "ret": period_returns,
    })
    df["year"] = df["date"].dt.year
    df["month"] = df["date"].dt.month
    grp = df.groupby(["year", "month"])["ret"].apply(lambda s: float(np.prod(1.0 + s) - 1.0) * 100.0)
    years = sorted(df["year"].unique())
    out = []
    for y in years:
        months: list[float | None] = []
        for m in range(1, 13):
            v = grp.get((y, m))
            months.append(round(float(v), 1) if v is not None else None)
        out.append({"year": int(y), "months": months})
    return out


def _summary_cards(perf: dict) -> list[dict]:
    """The eight headline cards the Backtests page renders (label/value/tone)."""
    def tone(v, good_high=True):
        if v == 0:
            return "neutral"
        return "bull" if (v > 0) == good_high else "bear"
    return [
        {"label": "CAGR", "value": f"{perf['cagr'] * 100:.1f}%", "tone": tone(perf["cagr"])},
        {"label": "Sharpe Ratio", "value": f"{perf['sharpe']:.2f}", "tone": "neutral"},
        {"label": "Sortino Ratio", "value": f"{perf['sortino']:.2f}", "tone": "neutral"},
        {"label": "Max Drawdown", "value": f"{perf['maxDrawdown'] * 100:.1f}%", "tone": "bear"},
        {"label": "Volatility (ann.)", "value": f"{perf['volatility'] * 100:.1f}%", "tone": "neutral"},
        {"label": "Turnover", "value": f"{perf['turnover'] * 100:.0f}%", "tone": "neutral"},
        {"label": "Win Rate", "value": f"{perf['winRate'] * 100:.1f}%", "tone": tone(perf["winRate"] - 0.5)},
        {"label": "Profit Factor", "value": f"{perf['profitFactor']:.2f}", "tone": tone(perf["profitFactor"] - 1.0)},
    ]


# --- orchestration ---
def _load_prices() -> tuple[dict, dict]:
    """Nested {date->{ticker->close}} and {date->close} for QQQ, from data/raw."""
    ohlcv = pd.read_parquet(settings.raw_dir / "ohlcv.parquet")[["date", "ticker", "close"]]
    pivot = ohlcv.pivot(index="date", columns="ticker", values="close")
    close = {d: {t: v for t, v in row.items() if pd.notna(v)} for d, row in pivot.to_dict("index").items()}
    bdf = pd.read_parquet(settings.raw_dir / "benchmark.parquet")
    bench = {d: float(c) for d, c in zip(bdf["date"], bdf["close"], strict=False)}
    return close, bench


def _record_trial(cfg: BacktestConfig, result: dict) -> None:
    """Log this run to the trial registry."""
    try:
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from ml.research.trial_registry import log_trial

        m = result["metrics"]
        keys = ("cagr", "sharpe", "sortino", "maxDrawdown", "totalReturn",
                "benchTotalReturn", "turnover", "winRate", "profitFactor")
        log_trial(
            kind="backtest",
            config=asdict(cfg),
            metrics={**{k: m.get(k) for k in keys}, "nObs": result["window"]["rebalances"]},
            tags=["walk-forward", "net-of-cost"],
            notes=f"{result['window']['start']}..{result['window']['end']}",
        )
    except Exception:  # noqa: BLE001 - logging a trial must never break a backtest
        pass


def run_backtest(
    cfg: BacktestConfig | None = None, force_oos: bool = False, log_trial: bool = True
) -> dict:
    """Full pipeline from OOS predictions toportfolio simulation to result dict.

    Every run gets logged to the trial registry unless log_trial=False, so the
    count and spread of trials are there when we want to check for selection bias.
    """
    cfg = cfg or BacktestConfig()
    oos = generate_oos_predictions(force=force_oos)
    close, bench = _load_prices()
    result = simulate(oos, close, bench, cfg)
    result["generatedAt"] = datetime.now(UTC).isoformat()
    if log_trial:
        _record_trial(cfg, result)
    return result


def main() -> None:
    cfg = BacktestConfig()
    print(f"Backtest · {cfg.rebalance} rebalance · top {cfg.top_n} · "
          f"costs {cfg.commission_bps + cfg.slippage_bps:.0f}bps round-trip")
    result = run_backtest(cfg, force_oos=False)
    BACKTEST_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_CACHE.write_text(json.dumps(result, indent=2))

    m, w = result["metrics"], result["window"]
    print(f"  window     {w['start']} … {w['end']}  ({w['rebalances']} rebalances)")
    print(f"  CAGR       {m['cagr'] * 100:6.2f}%   (QQQ {m['benchCagr'] * 100:.2f}%)")
    print(f"  total ret  {m['totalReturn'] * 100:6.2f}%   (QQQ {m['benchTotalReturn'] * 100:.2f}%)")
    print(f"  Sharpe     {m['sharpe']:.2f}   Sortino {m['sortino']:.2f}   vol {m['volatility'] * 100:.1f}%")
    print(f"  maxDD      {m['maxDrawdown'] * 100:6.2f}%   time-underwater {m['timeUnderWater']['fraction'] * 100:.0f}%")
    print(f"  turnover   {m['turnover'] * 100:.0f}%/yr   win {m['winRate'] * 100:.1f}%   PF {m['profitFactor']:.2f}")
    print(f"  trades     {result['tradeCount']}   benchCorr {m['benchCorrelation']}   beta {m['beta']}")
    print(f"  saved      {RESULT_CACHE.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
