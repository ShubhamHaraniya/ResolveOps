"""
ResolveOps FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db.session import init_db
from app.api.health import router as health_router
from app.api.tickets import router as tickets_router
from app.api.runs import router as runs_router
from app.api.approvals import router as approvals_router
from app.api.customers import router as customers_router
from app.api.audit import router as audit_router
from app.api.analytics import router as analytics_router
from app.api.policies import router as policies_router
from app.api.webhooks import router as webhooks_router
from app.api.copilot import router as copilot_router
from app.api.admin import router as admin_router

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    log.info("resolveops.startup", version=settings.version, env=settings.environment)

    # Initialize real database tables
    try:
        await init_db()
        from app.db.seed import seed_initial_data
        await seed_initial_data(include_demo_history=settings.seed_demo_data)
    except Exception as e:
        log.warning("db.init_failed_in_lifespan", error=str(e))

    # Persist gateway audit events into the hash-chained audit_log table
    from app.audit.gateway_sink import flush_pending, persist_gateway_event
    from services.gateway import gateway
    gateway.set_audit_sink(persist_gateway_event)

    # Verify connectivity to dependencies
    await _verify_dependencies()

    yield  # App is running

    await flush_pending()
    gateway.set_audit_sink(None)
    log.info("resolveops.shutdown")


async def _verify_dependencies():
    """Check all required services are reachable. Fast timeout, don't crash."""
    import asyncpg
    import redis.asyncio as aioredis
    from qdrant_client import AsyncQdrantClient

    # Postgres
    try:
        conn = await asyncpg.connect(settings.database_url, timeout=1)
        await conn.close()
        log.info("dep.postgres", status="connected")
    except Exception:
        log.info("dep.postgres", status="unreachable", note="Using in-memory/sqlite data store for local dev")

    # Redis
    try:
        r = aioredis.from_url(settings.redis_url)
        await r.ping()
        await r.aclose()
        log.info("dep.redis", status="connected")
    except Exception:
        log.info("dep.redis", status="unreachable", note="Using in-memory cache for local dev")

    # Qdrant
    try:
        client = AsyncQdrantClient(url=settings.qdrant_url, timeout=1, check_compatibility=False)
        await client.get_collections()
        await client.close()
        log.info("dep.qdrant", status="connected")
    except Exception:
        log.info("dep.qdrant", status="unreachable", note="Using local policy documents for local dev")


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
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(tickets_router, prefix="/api", tags=["Tickets"])
    app.include_router(runs_router, prefix="/api", tags=["Runs"])
    app.include_router(approvals_router, prefix="/api", tags=["Approvals"])
    app.include_router(customers_router, prefix="/api", tags=["Customers"])
    app.include_router(audit_router, prefix="/api", tags=["Audit"])
    app.include_router(analytics_router, prefix="/api", tags=["Analytics"])
    app.include_router(policies_router, prefix="/api", tags=["Policies"])
    app.include_router(webhooks_router, prefix="/api", tags=["Webhooks"])
    app.include_router(copilot_router, prefix="/api", tags=["Copilot"])
    app.include_router(admin_router, prefix="/api", tags=["Admin"])

    @app.get("/")
    async def root():
        return {
            "app": "ResolveOps",
            "tagline": "Governed AI Support Operations Platform",
            "status": "online",
            "version": settings.version,
            "docs": "/docs",
            "health": "/health",
            "ready": "/ready",
        }

    return app


app = create_app()
