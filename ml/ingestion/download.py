"""
Stage 1 — Ingestion.

Download real daily OHLCV for the universe (+ benchmark) and store it
point-in-time as long-format parquet under data/raw/.

Uses Yahoo's public chart API directly via `requests` (more reliable across
networks than yfinance's cookie/crumb handshake). Prices are dividend/split
adjusted via the adjclose ratio.

    python -m ml.ingestion.download --start 2018-01-01

Output:
    data/raw/ohlcv.parquet      [date, ticker, open, high, low, close, volume]
    data/raw/benchmark.parquet  [date, close]   (QQQ, adjusted)
"""
from __future__ import annotations

import argparse
import time

import pandas as pd
import requests

from ml import paths
from ml.universe import BENCHMARK, UNIVERSE

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OHLCV_COLS = ["date", "ticker", "open", "high", "low", "close", "volume"]


def fetch_history(ticker: str, start: str, end: str | None, retries: int = 3) -> pd.DataFrame:
    """Fetch adjusted daily OHLCV for one ticker from Yahoo's chart API."""
    p1 = int(pd.Timestamp(start).timestamp())
    p2 = int(pd.Timestamp(end).timestamp()) if end else int(pd.Timestamp.utcnow().timestamp())
    params = {"period1": p1, "period2": p2, "interval": "1d", "events": "div,splits"}

    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(CHART_URL.format(ticker=ticker), params=params,
                             headers=HEADERS, timeout=20)
            r.raise_for_status()
            result = r.json()["chart"]["result"]
            if not result:
                raise ValueError("empty result")
            res = result[0]
            ts = res["timestamp"]
            q = res["indicators"]["quote"][0]
            adj = res["indicators"].get("adjclose", [{}])[0].get("adjclose", q["close"])

            df = pd.DataFrame({
                "date": pd.to_datetime(ts, unit="s").tz_localize(None).normalize(),
                "open": q["open"], "high": q["high"], "low": q["low"],
                "close": q["close"], "adjclose": adj, "volume": q["volume"],
            }).dropna(subset=["close", "adjclose"])

            # Adjust OHLC by the adjclose/close ratio (handles splits & dividends).
            ratio = df["adjclose"] / df["close"]
            for c in ("open", "high", "low"):
                df[c] = df[c] * ratio
            df["close"] = df["adjclose"]
            df["ticker"] = ticker
            return df[OHLCV_COLS]
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(0.8 * (attempt + 1))
    print(f"  ! {ticker}: {last_err}")
    return pd.DataFrame(columns=OHLCV_COLS)


def download(tickers: list[str], start: str, end: str | None) -> pd.DataFrame:
    print(f"Downloading {len(tickers)} tickers from {start} …")
    frames, ok = [], 0
    for i, t in enumerate(tickers):
        df = fetch_history(t, start, end)
        if not df.empty:
            frames.append(df)
            ok += 1
        time.sleep(0.15)  # be polite to the API
        if (i + 1) % 10 == 0:
            print(f"  …{i + 1}/{len(tickers)}")
    if not frames:
        raise RuntimeError("No data returned for any ticker.")
    out = pd.concat(frames, ignore_index=True)
    out = out.dropna(subset=["close"]).sort_values(["ticker", "date"]).reset_index(drop=True)
    print(f"  → {ok}/{len(tickers)} tickers, {len(out):,} rows, "
          f"{out['date'].min().date()} … {out['date'].max().date()}")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Download OHLCV for the universe.")
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=None)
    ap.add_argument("--tickers", default=None,
                    help="Comma-separated subset (default: full universe).")
    args = ap.parse_args()

    paths.ensure_dirs()
    tickers = (
        [t.strip().upper() for t in args.tickers.split(",")]
        if args.tickers else UNIVERSE
    )

    ohlcv = download(tickers, args.start, args.end)
    ohlcv.to_parquet(paths.OHLCV_PATH, index=False)
    print(f"Saved {paths.OHLCV_PATH.relative_to(paths.REPO_ROOT)}")

    bench = download([BENCHMARK], args.start, args.end)[["date", "close"]]
    bench.to_parquet(paths.BENCHMARK_PATH, index=False)
    print(f"Saved {paths.BENCHMARK_PATH.relative_to(paths.REPO_ROOT)}")


if __name__ == "__main__":
    main()
