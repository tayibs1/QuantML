"""QuantML ML pipeline: ingestion -> features -> training -> inference.

Everything here writes artifacts into data/ and the FastAPI backend reads them.
The ML side never executes trades, it only produces signals.
"""
# Windows cp1252 chokes on the unicode in our progress prints, so force UTF-8.
import sys as _sys

for _stream in (_sys.stdout, _sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass
