"""Async database layer (SQLAlchemy 2.0 + asyncio).

Works against PostgreSQL in production (asyncpg driver, see
docker-compose.yml) and SQLite (aiosqlite) for local dev and tests.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def normalize_db_url(url: str) -> str:
    """Accept Postgres URLs as pasted from Neon/Vercel/Heroku dashboards.

    Those dashboards emit libpq-style URLs; the asyncpg driver needs
    the SQLAlchemy dialect prefix, `ssl=` instead of `sslmode=`, and
    no `channel_binding` parameter.
    """
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgres://")
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    url = url.replace("sslmode=", "ssl=")
    url = url.replace("&channel_binding=require", "")
    url = url.replace("?channel_binding=require&", "?")
    url = url.replace("?channel_binding=require", "")
    return url.rstrip("?&")


engine = create_async_engine(normalize_db_url(settings.database_url), echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    """Create tables on startup (simple projects; use Alembic at scale)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding one session per request."""
    async with SessionLocal() as session:
        yield session
