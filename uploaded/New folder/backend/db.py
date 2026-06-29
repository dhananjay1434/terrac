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
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in environment")

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


async def init_db():
    """Initialize database tables."""
    if os.environ.get("DMRV_SKIP_MIGRATIONS") == "1":
        return
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
