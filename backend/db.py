"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from models import Base

# PostgreSQL connection URL from environment
_DATABASE_URL_RAW = os.environ.get("DATABASE_URL")
if not _DATABASE_URL_RAW:
    raise RuntimeError(
        "DATABASE_URL env var is required. Refusing to fall back to a local default."
    )
DATABASE_URL = _DATABASE_URL_RAW

# T3.1: production connection-pool tuning. pool_size/max_overflow are ONLY
# valid for a real server-side pool (Postgres/asyncpg). SQLite/aiosqlite uses
# SingletonThreadPool/StaticPool and raises TypeError on those kwargs, and the
# test suite runs on sqlite+aiosqlite:///:memory: — so apply them conditionally
# on the URL scheme. Sizes are env-tunable for deploy (engine is built once at
# import, so a live re-read is unnecessary here).
_engine_kwargs: dict = {"echo": False, "future": True}
if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update(
        pool_pre_ping=True,
        pool_size=int(os.environ.get("DMRV_POOL_SIZE", "10")),
        max_overflow=int(os.environ.get("DMRV_POOL_MAX_OVERFLOW", "20")),
    )

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency for database sessions."""
    async with SessionLocal() as session:
        yield session


from alembic.config import Config
from alembic import command
import asyncio
from pathlib import Path


async def init_db():
    """Run Alembic migrations to head. Idempotent. No data seeding.

    Phase R2: the previous unconditional seeding of a well-known development
    EnrollmentToken (with used_at reset to None on every boot) was a permanent
    enrollment backdoor in production. It is removed entirely — a flag-gated
    re-seed would still be a backdoor on misconfiguration. Local dev mints a token
    via /api/v1/admin/mint-token (requires DMRV_ADMIN_SECRET).
    """
    if os.environ.get("DMRV_SKIP_MIGRATIONS") != "1":
        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))
        await asyncio.to_thread(command.upgrade, cfg, "head")
