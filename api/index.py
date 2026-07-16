"""Vercel serverless entry point.

Vercel's Python runtime looks for an ASGI `app` in this module and
wraps it in a serverless function. All routes are rewritten here by
vercel.json. The regular server entry point (uvicorn app.main:app)
is unchanged for local dev and Docker.
"""

from app.main import app  # noqa: F401
