"""Tests for dashboard-pasted Postgres URL normalization."""

from app.database import normalize_db_url


def test_neon_style_url_is_normalized():
    url = ("postgresql://user:pw@ep-x.aws.neon.tech/db"
           "?sslmode=require&channel_binding=require")
    out = normalize_db_url(url)
    assert out == "postgresql+asyncpg://user:pw@ep-x.aws.neon.tech/db?ssl=require"


def test_heroku_style_postgres_prefix():
    out = normalize_db_url("postgres://u:p@host:5432/db")
    assert out.startswith("postgresql+asyncpg://")


def test_sqlite_url_untouched():
    url = "sqlite+aiosqlite:///./dev.db"
    assert normalize_db_url(url) == url


def test_already_normalized_url_untouched():
    url = "postgresql+asyncpg://u:p@host/db?ssl=require"
    assert normalize_db_url(url) == url
