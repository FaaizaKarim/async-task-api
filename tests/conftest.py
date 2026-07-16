"""Shared test fixtures.

The test suite runs fully offline against SQLite (aiosqlite); the
environment is configured *before* the app modules are imported so the
async engine binds to the test database, and the rate limit is raised
so functional tests don't trip it (the limiter has its own test).
"""

import os
import tempfile
from pathlib import Path

_test_db = Path(tempfile.gettempdir()) / "task_api_test.db"
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db.as_posix()}"
os.environ["RATE_LIMIT_REQUESTS"] = "10000"
os.environ["JWT_SECRET"] = "test-secret"

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import Base, engine
from app.main import app


@pytest.fixture
async def client():
    """Fresh schema + async HTTP client per test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register + log in a user; return Authorization headers."""
    await client.post(
        "/auth/register",
        json={"email": "faaiza@example.com", "password": "s3cure-pass"},
    )
    resp = await client.post(
        "/auth/login",
        data={"username": "faaiza@example.com", "password": "s3cure-pass"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
