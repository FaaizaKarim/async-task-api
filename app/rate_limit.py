"""Sliding-window rate limiter (in-memory, per client IP).

Suitable for a single instance; swap the store for Redis when running
multiple replicas. Implemented as an ASGI-level FastAPI dependency so
it composes with route dependencies and is trivial to test.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from .config import settings


class RateLimiter:
    """Allows `max_requests` per `window_s` seconds per client key."""

    def __init__(self, max_requests: int, window_s: float) -> None:
        self.max_requests = max_requests
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def check(self, key: str) -> None:
        """Record a hit for `key`; raise 429 if over the limit."""
        now = time.monotonic()
        async with self._lock:
            window = self._hits[key]
            while window and now - window[0] > self.window_s:
                window.popleft()
            if len(window) >= self.max_requests:
                retry_after = self.window_s - (now - window[0])
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded",
                    headers={"Retry-After": f"{max(1, int(retry_after))}"},
                )
            window.append(now)


limiter = RateLimiter(settings.rate_limit_requests, settings.rate_limit_window_s)


async def rate_limit(request: Request) -> None:
    """FastAPI dependency — keyed by client IP."""
    client_ip = request.client.host if request.client else "unknown"
    await limiter.check(client_ip)
