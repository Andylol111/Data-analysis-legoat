#!/usr/bin/env bash
# Install deps, regenerate outputs, start local dashboard.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# Clear port 5050 (Flask dev server) so we can bind without "Address already in use"
PORT=5050
if lsof -ti:"$PORT" >/dev/null 2>&1; then
  echo "Killing processes on port $PORT …"
  lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
  sleep 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating .venv …"
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate

echo "Installing dependencies …"
pip install -q -r requirements.txt

echo "Running analysis …"
python3 run_analysis.py

echo ""
echo "Starting web server at http://127.0.0.1:5050"
echo "Press Ctrl+C to stop."
echo ""
exec python3 webapp/app.py
