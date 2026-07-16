# Async Task Management REST API

A production-style **async REST API** built with **FastAPI + SQLAlchemy 2.0 (asyncio)**: JWT authentication, per-IP rate limiting, ownership-enforced CRUD, PostgreSQL, Docker, and a fully offline test suite.

## Features

**Async end to end** — async route handlers, async SQLAlchemy engine (asyncpg for PostgreSQL, aiosqlite for dev/tests), one DB session per request via dependency injection.

**Secure by design:**

- Passwords hashed with PBKDF2-HMAC-SHA256 (per-user salt, 600k iterations), verified with constant-time comparison — never stored or returned in plaintext.
- Short-lived signed JWTs (OAuth2 password flow); the token subject is re-validated against the DB on every request.
- Ownership enforced *in the query*: a valid token for user A can never read or mutate user B's tasks (no IDOR), and cross-user probes return 404, not 403 — no existence oracle.
- Login verifies a dummy hash when the email is unknown, so response timing doesn't reveal registered emails.
- Separate input/output Pydantic schemas — server-controlled fields can't be set by clients, secrets can't leak into responses.
- Sliding-window rate limiter (HTTP 429 + Retry-After), keyed by client IP.
- Docker image runs as non-root; secrets come from environment, never source.

## API

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Create account |
| POST | `/auth/login` | — | OAuth2 password flow → JWT |
| POST | `/tasks` | JWT | Create task |
| GET | `/tasks?status=&limit=&offset=` | JWT | List own tasks (filter + pagination) |
| GET | `/tasks/{id}` | JWT | Get own task |
| PATCH | `/tasks/{id}` | JWT | Partial update |
| DELETE | `/tasks/{id}` | JWT | Delete |
| GET | `/health` | — | Liveness probe |

Interactive OpenAPI/Swagger docs at `/docs`.

## Run it

```bash
# local dev (SQLite, no setup)
pip install -r requirements-dev.txt
uvicorn app.main:app --reload

# production-style (PostgreSQL + Docker)
echo "JWT_SECRET=$(openssl rand -hex 32)" > .env
docker compose up --build
```

## Tests

```bash
pytest -v
```

13 tests, fully offline (SQLite): auth flow, password hashing/salting, token validation, full CRUD lifecycle, pagination and filtering, cross-user authorization, input validation, and the rate limiter. CI runs the suite on Python 3.11/3.12 and builds the Docker image.

## Architecture notes

- `config.py` — 12-factor settings from environment variables.
- `database.py` — async engine/session factory; `Base` for ORM models.
- `auth.py` — hashing + JWT creation + `get_current_user` dependency.
- `rate_limit.py` — asyncio-safe sliding-window limiter (swap store for Redis to scale horizontally).
- `routers/` — thin route handlers; authorization lives in queries, validation in schemas.

Trade-offs are documented in code comments — e.g., `create_all` on startup instead of Alembic migrations (right-sized for the project), and an in-memory limiter (single instance) with the Redis upgrade path noted.

## Tech

Python 3.11+ · FastAPI · SQLAlchemy 2.0 async · PostgreSQL / asyncpg · PyJWT · Docker · pytest / pytest-asyncio · GitHub Actions
