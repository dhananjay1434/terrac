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


def normalize_db_url(url: str) -> str:
    """Upgrade a bare Postgres URL to the async driver our engine requires.

    Managed Postgres providers (Render, Heroku, Supabase, Railway) hand out
    ``postgres://…`` or ``postgresql://…`` with NO async driver. Both our runtime
    engine (create_async_engine) and the startup Alembic migration (env.py online
    mode is async) require an async driver, so a bare Postgres scheme is rewritten
    to ``postgresql+asyncpg://``. Any URL that already names a driver
    (``+asyncpg``, ``+psycopg2``, ``+aiosqlite``) or a non-Postgres backend is
    returned unchanged — so operators can still pin a driver explicitly.
    """
    if url.startswith("postgres://"):  # legacy Heroku-style scheme
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):  # bare scheme, no +driver
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    return url


DATABASE_URL = normalize_db_url(_DATABASE_URL_RAW)
# Write the canonical form back so Alembic's env.py (which re-reads
# os.environ["DATABASE_URL"] and builds an async engine) inherits the async
# driver too — otherwise the startup migration would crash on a bare URL.
os.environ["DATABASE_URL"] = DATABASE_URL

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
