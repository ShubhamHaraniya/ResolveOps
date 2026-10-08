"""
Health and readiness endpoints.
GET /health — liveness probe
GET /ready  — readiness probe (checks all dependencies)
"""
import time
from datetime import datetime, UTC

import asyncpg
import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

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


@router.get("/ready", response_model=ReadyResponse)
async def ready():
    """
    Readiness probe — checks all critical dependencies.
    Returns 200 if all healthy, 503 if any degraded.
    """
    deps: dict[str, DependencyStatus] = {}
    all_healthy = True

    # Postgres
    t0 = time.monotonic()
    try:
        conn = await asyncpg.connect(settings.database_url, timeout=3)
        await conn.fetchval("SELECT 1")
        await conn.close()
        deps["postgres"] = DependencyStatus(
            status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1)
        )
    except Exception as e:
        deps["postgres"] = DependencyStatus(status="unreachable", error=str(e)[:100])
        all_healthy = False

    # Redis
    t0 = time.monotonic()
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=3)
        await r.ping()
        await r.aclose()
        deps["redis"] = DependencyStatus(
            status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1)
        )
    except Exception as e:
        deps["redis"] = DependencyStatus(status="unreachable", error=str(e)[:100])
        all_healthy = False

    # Qdrant
    t0 = time.monotonic()
    try:
        from qdrant_client import AsyncQdrantClient
        client = AsyncQdrantClient(url=settings.qdrant_url, timeout=3)
        await client.get_collections()
        await client.close()
        deps["qdrant"] = DependencyStatus(
            status="ok", latency_ms=round((time.monotonic() - t0) * 1000, 1)
        )
    except Exception as e:
        deps["qdrant"] = DependencyStatus(status="degraded", error=str(e)[:100])
        # Qdrant degraded doesn't block readiness (RAG is non-critical for basic ops)

    status_code = 200 if all_healthy else 503
    response = ReadyResponse(
        status="ready" if all_healthy else "degraded",
        dependencies=deps,
    )

    # FastAPI doesn't allow dynamic status codes in response_model mode directly
    # so we use a plain Response here
    from fastapi.responses import JSONResponse
    return JSONResponse(content=response.model_dump(), status_code=status_code)
