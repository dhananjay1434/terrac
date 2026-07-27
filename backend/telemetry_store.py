"""Dialect-aware idempotent point inserts (audit A2). Duplicate (batch,
channel, ts) rows are silently skipped — chunk retries and overlapping
re-aggregations are free, never errors."""
from sqlalchemy.ext.asyncio import AsyncSession

from models import TelemetryPoint


async def insert_points(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    stmt = insert(TelemetryPoint).values(rows).on_conflict_do_nothing(
        index_elements=["batch_uuid", "channel", "ts"]
    )
    result = await session.execute(stmt)
    return result.rowcount or 0
