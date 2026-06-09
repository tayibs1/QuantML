"""QuantML ML pipeline: ingestion -> features -> training -> inference.

The pipeline writes artifacts to `data/`; the FastAPI backend reads them. The
ML engine NEVER executes trades — it only produces signals.
"""
# Force UTF-8 console output so progress prints don't crash on Windows cp1252.
import sys as _sys

for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
