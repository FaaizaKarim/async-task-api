"""Application entry point.

Run locally:
    uvicorn app.main:app --reload

Interactive docs: http://localhost:8000/docs (OpenAPI/Swagger).
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import RedirectResponse

from .database import init_db
from .rate_limit import rate_limit
from .routers import auth, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Async Task Management API",
    version="1.0.0",
    description=(
        "Async REST API built with FastAPI: JWT authentication, per-IP "
        "rate limiting, PostgreSQL via SQLAlchemy 2.0 async, Docker-ready."
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
async def root() -> RedirectResponse:
    """Convenience: the API root redirects to the interactive docs."""
    return RedirectResponse(url="/docs")
