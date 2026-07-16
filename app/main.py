"""Application entry point.

Run locally:
    uvicorn app.main:app --reload

/       — single-page task-board frontend (vanilla JS, no build step)
/docs   — interactive OpenAPI/Swagger documentation
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from .database import init_db
from .rate_limit import rate_limit
from .routers import auth, tasks

_STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Async Task Management API",
    version="1.1.0",
    description=(
        "Async REST API built with FastAPI: JWT authentication, per-IP "
        "rate limiting, PostgreSQL via SQLAlchemy 2.0 async, Docker-ready. "
        "A vanilla-JS task-board frontend is served at the root path."
    ),
    lifespan=lifespan,
    dependencies=[Depends(rate_limit)],
)

app.include_router(auth.router)
app.include_router(tasks.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
async def root() -> FileResponse:
    """Serve the task-board frontend."""
    return FileResponse(_STATIC / "index.html")
