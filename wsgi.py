"""
WSGI entry for production servers, e.g.:

  gunicorn -w 4 -b 127.0.0.1:5050 --timeout 120 "wsgi:app"

Bind to localhost only unless you have TLS and auth in front.
"""
from webapp.app import app

__all__ = ["app"]
