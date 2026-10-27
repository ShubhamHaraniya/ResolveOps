"""
backend/app/db/session.py
SQLAlchemy session and engine setup with automatic dual-mode fallback.
Connects to PostgreSQL in production/docker; cleanly falls back to SQLite (aiosqlite)
when PostgreSQL is not running locally.
"""
import socket
from collections.abc import AsyncGenerator
from pathlib import Path
from urllib.parse import urlparse

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models import Base

log = structlog.get_logger()

BACKEND_DIR = Path(__file__).resolve().parents[2]
CANONICAL_DB_PATH = (BACKEND_DIR / "resolveops.db").as_posix()
SQLITE_FALLBACK_URL = f"sqlite+aiosqlite:///{CANONICAL_DB_PATH}"


def _is_postgres_alive(url: str) -> bool:
    """Quick TCP probe of the host/port in the configured Postgres URL."""
    parsed = urlparse(url)
    try:
        with socket.create_connection((parsed.hostname or "localhost", parsed.port or 5432), timeout=0.5):
            return True
    except OSError:
        return False


# Determine database URL
_raw_url = settings.database_url or SQLITE_FALLBACK_URL

if _raw_url.startswith(("postgresql://", "postgresql+")) and _is_postgres_alive(_raw_url):
    _async_url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(
        _async_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        echo=False,
    )
    log.info("db.engine.using_postgres", host=urlparse(_raw_url).hostname)
elif _raw_url.startswith("sqlite"):
    engine = create_async_engine(_raw_url, echo=False)
    log.info("db.engine.using_sqlite", url=_raw_url)
else:
    engine = create_async_engine(SQLITE_FALLBACK_URL, echo=False)
    log.info("db.engine.using_sqlite_fallback", url=SQLITE_FALLBACK_URL)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Initialize database tables. Automatically creates tables if not exist."""
    global engine
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("db.init.success", url=str(engine.url))
    except Exception as e:
        log.warning("db.init.primary_db_failed_switching_to_sqlite", error=str(e))
        engine = create_async_engine(SQLITE_FALLBACK_URL, echo=False)
        # Re-bind the shared sessionmaker so modules that imported it keep working.
        AsyncSessionLocal.configure(bind=engine)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        log.info("db.init.sqlite_ready", path=SQLITE_FALLBACK_URL)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
