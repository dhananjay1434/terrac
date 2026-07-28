"""M2.1 — telemetry chunk/point schema: chunk idempotency (UNIQUE), point-level
idempotency (conflict-ignoring insert_points), round-trip."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from models import TelemetryChunk, TelemetryPoint
from telemetry_store import insert_points

_T0 = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


def _chunk(**over) -> TelemetryChunk:
    base = dict(
        session_uuid="s-1",
        batch_uuid="b-1",
        device_id="dev-1",
        channel="T1",
        t_start=_T0,
        t_end=_T0 + timedelta(minutes=10),
        sample_period_s=10.0,
        payload_json="{}",
        signature="sig-abc",
    )
    base.update(over)
    return TelemetryChunk(**base)


@pytest.mark.asyncio
async def test_chunk_unique_is_idempotent(session_factory):
    async with session_factory() as s:
        s.add(_chunk())
        await s.commit()
    # identical (batch, channel, t_start, signature) → rejected
    async with session_factory() as s:
        s.add(_chunk())
        with pytest.raises(IntegrityError):
            await s.commit()
    # a different signature is a distinct chunk → allowed
    async with session_factory() as s:
        s.add(_chunk(signature="sig-xyz"))
        await s.commit()
    async with session_factory() as s:
        assert len((await s.execute(select(TelemetryChunk))).scalars().all()) == 2


@pytest.mark.asyncio
async def test_insert_points_conflict_ignoring(session_factory):
    rows = [
        {
            "batch_uuid": "b-1",
            "channel": "T1",
            "ts": _T0 + timedelta(seconds=10 * i),
            "value": 400.0 + i,
        }
        for i in range(5)
    ]
    async with session_factory() as s:
        assert await insert_points(s, rows) == 5
        await s.commit()
    async with session_factory() as s:
        assert await insert_points(s, rows) == 0  # all duplicates silently skipped
        await s.commit()
    async with session_factory() as s:
        assert len((await s.execute(select(TelemetryPoint))).scalars().all()) == 5
    async with session_factory() as s:
        assert await insert_points(s, []) == 0  # empty → 0, no error


@pytest.mark.asyncio
async def test_points_roundtrip_values(session_factory):
    rows = [
        {"batch_uuid": "b-2", "channel": "LOAD", "ts": _T0, "value": 121.6},
        {"batch_uuid": "b-2", "channel": "LOAD", "ts": _T0 + timedelta(seconds=10), "value": 130.0},
    ]
    async with session_factory() as s:
        await insert_points(s, rows)
        await s.commit()
    async with session_factory() as s:
        got = (
            await s.execute(
                select(TelemetryPoint.value)
                .where(TelemetryPoint.batch_uuid == "b-2")
                .order_by(TelemetryPoint.ts)
            )
        ).scalars().all()
        assert got == [121.6, 130.0]
