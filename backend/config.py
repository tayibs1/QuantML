"""
Central configuration for the QuantML backend + ML pipeline.

Reads from a repo-root `.env` (copy from `.env.example`). All paths are resolved
relative to the repo root, so it works whether you run uvicorn from `backend/`
or scripts from the repo root.

The execution flags here enforce the core architecture rule:

    Signal Engine  →  Portfolio/Risk  →  Execution Adapter
       (predict)        (propose orders)     (backtest | paper | live)

Live trading is hard-gated behind `LIVE_TRADING_ENABLED=false`.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[1]

ExecutionMode = Literal["backtest", "paper", "live"]
BrokerProvider = Literal["none", "alpaca"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # look for .env at the repo root or in backend/, ignore unknown keys
        env_file=(REPO_ROOT / ".env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- app / api ---
    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- market data ---
    market_data_provider: str = "yfinance"
    alpaca_api_key: str = ""
    alpaca_api_secret: str = ""
    alpaca_data_feed: str = "iex"
    polygon_api_key: str = ""
    tiingo_api_key: str = ""

    # --- ml / model ---
    mlflow_tracking_uri: str = "./mlruns"
    default_model: str = "XGBoost-v3"
    universe: str = "NASDAQ100"

    # --- rag (not building this yet) ---
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- execution architecture ---
    # backtest = simulated (this is what's built), paper = Alpaca paper (stub),
    # live = real orders (off). The ML engine never executes - only the adapter
    # picked here ever touches the proposed orders.
    execution_mode: ExecutionMode = "backtest"
    broker_provider: BrokerProvider = "none"
    live_trading_enabled: bool = False
    trading_mode: str = "paper"

    # --- derived paths (always absolute, anchored at the repo root) ---
    @property
    def data_dir(self) -> Path:
        return REPO_ROOT / "data"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"

    @property
    def models_dir(self) -> Path:
        return self.data_dir / "models"

    @property
    def signals_dir(self) -> Path:
        return self.data_dir / "signals"

    @property
    def vectorstore_dir(self) -> Path:
        return self.data_dir / "vectorstore"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for d in (
            self.raw_dir,
            self.processed_dir,
            self.models_dir,
            self.signals_dir,
            self.vectorstore_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def assert_execution_allowed(self) -> None:
        """Hard gate: don't let live orders through unless someone flipped the flag."""
        if self.execution_mode == "live" and not self.live_trading_enabled:
            raise RuntimeError(
                "EXECUTION_MODE=live but LIVE_TRADING_ENABLED=false. "
                "Live trading is disabled by design. Set LIVE_TRADING_ENABLED=true "
                "only after full risk review."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
