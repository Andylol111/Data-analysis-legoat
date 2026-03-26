#!/usr/bin/env bash
# WSGI server (no analysis step). Use behind TLS + auth in production.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck source=/dev/null
source .venv/bin/activate
python3 -m pip install -q -r requirements.txt
# Use `python3 -m gunicorn` so the venv’s Gunicorn is used (avoids “gunicorn: command not found”).
exec python3 -m gunicorn -w 4 -b 127.0.0.1:5050 --timeout 120 "wsgi:app"
