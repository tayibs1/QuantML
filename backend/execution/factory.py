"""Select the execution adapter for the configured mode."""
from __future__ import annotations

from config import Settings
from config import settings as default_settings

from .backtest import BacktestExecutionAdapter
from .base import ExecutionAdapter
from .live import LiveExecutionAdapter
from .paper import PaperExecutionAdapter


def get_execution_adapter(settings: Settings = default_settings) -> ExecutionAdapter:
    """Return the adapter for settings.execution_mode, enforcing the live gate."""
    settings.assert_execution_allowed()
    mode = settings.execution_mode

    if mode == "backtest":
        return BacktestExecutionAdapter()
    if mode == "paper":
        return PaperExecutionAdapter(
            broker_provider=settings.broker_provider,
            api_key=settings.alpaca_api_key,
            api_secret=settings.alpaca_api_secret,
        )
    if mode == "live":
        return LiveExecutionAdapter(
            live_trading_enabled=settings.live_trading_enabled,
            broker_provider=settings.broker_provider,
        )
    raise ValueError(f"Unknown EXECUTION_MODE: {mode}")
