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
        "DATABASE_URL env var is required. "
        "Refusing to fall back to a local default."
    )
DATABASE_URL = _DATABASE_URL_RAW

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
)

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
    """Run Alembic migrations to head and seed test data. Idempotent."""
    if os.environ.get("DMRV_SKIP_MIGRATIONS") != "1":
        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))
        await asyncio.to_thread(command.upgrade, cfg, "head")

    # Seed the dev-token if it doesn't exist, and reset its used_at so we can reuse it
    from models import EnrollmentToken
    from sqlalchemy.future import select
    
    async with SessionLocal() as session:
        result = await session.execute(select(EnrollmentToken).where(EnrollmentToken.token == "dev-token"))
        token = result.scalar_one_or_none()
        if not token:
            session.add(EnrollmentToken(token="dev-token"))
        else:
            token.used_at = None
        await session.commit()

