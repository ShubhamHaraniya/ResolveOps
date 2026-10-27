"""
Health and readiness endpoints.
GET /health — liveness probe
GET /ready  — readiness probe (checks all dependencies)
"""
import time
from datetime import datetime, UTC

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.config import settings
from app.db import session as db_session

router = APIRouter()
log = structlog.get_logger()

_start_time = time.time()


class DependencyStatus(BaseModel):
    status: str  # "ok" | "degraded" | "unreachable"
    latency_ms: float | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    uptime_seconds: float
    timestamp: str


class ReadyResponse(BaseModel):
    status: str  # "ready" | "degraded"
    dependencies: dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse, status_code=200)
async def health():
    """Liveness probe — returns 200 if the process is alive."""
    return HealthResponse(
        status="ok",
        version=settings.version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _start_time, 2),
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/ready")
async def ready():
    """
    Readiness probe. Only the application database is required; Redis and Qdrant are
    reported but do not block readiness (Redis is only probed here; RAG falls back to an
    in-memory Qdrant when the server is unreachable).
    Returns 200 when the database answers, 503 otherwise.
    """
    deps: dict[str, DependencyStatus] = {}

    # Application database (whichever backend the engine ended up using)
    t0 = time.monotonic()
    backend = db_session.engine.url.get_backend_name()
    try:
        async with db_session.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        deps[f"database ({backend})"] = DependencyStatus(
            status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1)
        )
        db_ok = True
    except Exception as e:
        deps[f"database ({backend})"] = DependencyStatus(status="unreachable", error=str(e)[:100])
        db_ok = False

    # Redis (optional)
    t0 = time.monotonic()
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
        deps["redis"] = DependencyStatus(status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1))
    except Exception as e:
        deps["redis"] = DependencyStatus(status="unreachable", error=str(e)[:100])

    # Qdrant (optional)
    t0 = time.monotonic()
    try:
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(url=settings.qdrant_url, timeout=2, check_compatibility=False)
        await client.get_collections()
        await client.close()
        deps["qdrant"] = DependencyStatus(status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1))
    except Exception as e:
        deps["qdrant"] = DependencyStatus(status="unreachable", error=str(e)[:100])

    response = ReadyResponse(status="ready" if db_ok else "degraded", dependencies=deps)
    return JSONResponse(content=response.model_dump(), status_code=200 if db_ok else 503)
