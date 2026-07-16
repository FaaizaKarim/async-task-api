"""Application settings, loaded from environment variables.

Secure-coding note: secrets never live in source. DATABASE_URL and
JWT_SECRET come from the environment (docker-compose / CI secrets);
the defaults below are for local development only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get(
        "DATABASE_URL", "sqlite+aiosqlite:///./dev.db"
    )
    jwt_secret: str = os.environ.get("JWT_SECRET", "dev-only-change-me")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.environ.get("ACCESS_TOKEN_MINUTES", "30"))
    rate_limit_requests: int = int(os.environ.get("RATE_LIMIT_REQUESTS", "60"))
    rate_limit_window_s: int = int(os.environ.get("RATE_LIMIT_WINDOW_S", "60"))


settings = Settings()
