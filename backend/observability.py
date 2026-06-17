"""
Observability — request metrics + a Prometheus /metrics endpoint.

Hand-rolled exposition format, no prometheus_client dependency, to match the rest
of the codebase (the trial registry hand-rolls its stats the same way). Tracks
per-route request counts and latency, and exposes model/drift/data-quality gauges
read straight off the pipeline artifacts so a scrape reflects the live system, not a
snapshot taken at boot.

A request-tracing middleware stamps every response with an X-Request-ID and logs a
structured line, so a request can be followed end to end.
"""
from __future__ import annotations

import json
import logging
import threading
from pathlib import Path

from config import settings
from starlette.requests import Request

logger = logging.getLogger("quantml.access")

APP_VERSION = "0.2.0"
_DRIFT_LEVEL = {"OK": 0, "WARN": 1, "ALERT": 2}


class _Collector:
    """In-process counters. GIL plus a lock keeps the increments consistent."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, int], int] = {}
        self._duration_sum: dict[str, float] = {}
        self._duration_count: dict[str, int] = {}

    def record(self, method: str, path: str, status: int, seconds: float) -> None:
        with self._lock:
            key = (method, path, status)
            self._requests[key] = self._requests.get(key, 0) + 1
            self._duration_sum[path] = self._duration_sum.get(path, 0.0) + seconds
            self._duration_count[path] = self._duration_count.get(path, 0) + 1

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "requests": dict(self._requests),
                "duration_sum": dict(self._duration_sum),
                "duration_count": dict(self._duration_count),
            }


collector = _Collector()


def route_path(request: Request) -> str:
    """Matched route template (not the raw URL), to keep label cardinality bounded."""
    route = request.scope.get("route")
    return getattr(route, "path", None) or request.url.path


def _read(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, ValueError, OSError):
        return None


def _esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _artifact_gauges() -> list[str]:
    """Live model/drift/data-quality gauges, read from the pipeline artifacts."""
    out: list[str] = []
    card = _read(settings.models_dir / "model_card.json")
    model = (card.get("models") or [{}])[0] if card else {}
    if model.get("sharpe") is not None:
        out += ["# TYPE quantml_model_sharpe gauge",
                f"quantml_model_sharpe {model['sharpe']}"]
    if model.get("auc") is not None:
        out += ["# TYPE quantml_model_auc gauge", f"quantml_model_auc {model['auc']}"]

    drift = _read(settings.data_dir / "research" / "drift.json")
    if drift and drift.get("overall") in _DRIFT_LEVEL:
        out += ["# TYPE quantml_drift_status gauge",
                "# HELP quantml_drift_status feature drift 0=OK 1=WARN 2=ALERT",
                f"quantml_drift_status {_DRIFT_LEVEL[drift['overall']]}"]

    health = _read(settings.data_dir / "research" / "data_health.json")
    if health is not None:
        out += ["# TYPE quantml_data_quality_ok gauge",
                f"quantml_data_quality_ok {1 if health.get('ok') else 0}"]
    return out


def render() -> str:
    """Build the full Prometheus exposition text."""
    snap = collector.snapshot()
    lines = [
        "# HELP quantml_build_info Build information",
        "# TYPE quantml_build_info gauge",
        f'quantml_build_info{{version="{_esc(APP_VERSION)}"}} 1',
        "# HELP quantml_requests_total Total HTTP requests",
        "# TYPE quantml_requests_total counter",
    ]
    for (method, path, status), count in sorted(snap["requests"].items()):
        lines.append(
            f'quantml_requests_total{{method="{_esc(method)}",'
            f'path="{_esc(path)}",status="{status}"}} {count}'
        )

    lines += ["# HELP quantml_request_duration_seconds Request latency by route",
              "# TYPE quantml_request_duration_seconds summary"]
    for path, total in sorted(snap["duration_sum"].items()):
        p = _esc(path)
        lines.append(f'quantml_request_duration_seconds_sum{{path="{p}"}} {total:.6f}')
        lines.append(
            f'quantml_request_duration_seconds_count{{path="{p}"}} '
            f'{snap["duration_count"].get(path, 0)}'
        )

    lines += _artifact_gauges()
    return "\n".join(lines) + "\n"
