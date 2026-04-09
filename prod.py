"""Production entry for Gunicorn. Put TLS and auth in front; bind to localhost only if unsure.

  python3 -m gunicorn -w 4 -b 127.0.0.1:5050 --timeout 120 "prod:app"
"""
from webapp.app import app

__all__ = ["app"]
