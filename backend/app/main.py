"""
ResolveOps FastAPI Application Entry Point
"""
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.health import router as health_router
from app.api.tickets import router as tickets_router
from app.api.approvals import router as approvals_router
from app.api.customers import router as customers_router
from app.api.audit import router as audit_router
from app.api.analytics import router as analytics_router
from app.api.demo import router as demo_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    log.info("resolveops.startup", version=settings.version, env=settings.environment)

    # Verify connectivity to dependencies
    await _verify_dependencies()

    yield  # App is running

    log.info("resolveops.shutdown")


async def _verify_dependencies():
    """Check all required services are reachable. Log warnings, don't crash."""
    import asyncpg
    import redis.asyncio as aioredis
    from qdrant_client import AsyncQdrantClient

    # Postgres
    try:
        conn = await asyncpg.connect(settings.database_url, timeout=5)
        await conn.close()
        log.info("dep.postgres", status="ok")
    except Exception as e:
        log.warning("dep.postgres", status="unreachable", error=str(e))

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        log.info("dep.redis", status="ok")
    except Exception as e:
        log.warning("dep.redis", status="unreachable", error=str(e))

    # Qdrant
    try:
        client = AsyncQdrantClient(url=settings.qdrant_url, timeout=5)
        await client.get_collections()
        await client.close()
        log.info("dep.qdrant", status="ok")
    except Exception as e:
        log.warning("dep.qdrant", status="unreachable", error=str(e))


def create_app() -> FastAPI:
    app = FastAPI(
        title="ResolveOps API",
        description="Governed AI Support Operations Platform",
        version=settings.version,
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS — allow frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:3001",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(tickets_router, prefix="/api", tags=["Tickets"])
    app.include_router(approvals_router, prefix="/api", tags=["Approvals"])
    app.include_router(customers_router, prefix="/api", tags=["Customers"])
    app.include_router(audit_router, prefix="/api", tags=["Audit"])
    app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
    app.include_router(demo_router, prefix="/api", tags=["Demo"])

    return app


app = create_app()
