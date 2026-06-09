#!/usr/bin/env bash
# Start the QuantML frontend (3000) and backend (8000) together.
# Usage:  ./scripts/dev.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Starting QuantML backend (FastAPI :8000)..."
(
  cd "$ROOT/backend"
  [ -f .venv/bin/activate ] && source .venv/bin/activate
  uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

echo "Starting QuantML frontend (Next.js :3000)..."
(
  cd "$ROOT/frontend"
  npm run dev
) &
FRONTEND_PID=$!

echo ""
echo "QuantML running:"
echo "  web : http://localhost:3000"
echo "  api : http://localhost:8000/docs"

trap 'kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true' EXIT INT TERM
wait
