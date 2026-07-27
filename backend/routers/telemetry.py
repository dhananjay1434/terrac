"""/api/v2/telemetry — signed edge-telemetry ingest (blueprint §4.1, M2.2).

Chunk body (exactly what the device signs):
{
  "batch_uuid": "...", "channel": "T1",          # T1|T2|T3|T4|LOAD
  "t_start": "...Z", "sample_period_s": 10.0,
  "values": [412.5, 418.0, ...]                   # <= 720 per chunk (2 h @10 s)
}

Idempotent via the chunk UNIQUE (a retried chunk returns status=duplicate, 200).
Does NOT touch PyrolysisTelemetry or the credit engine. Each accepted chunk is
published on telemetry_bus for the live SSE stream (M2.4).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import telemetry_bus
from db import get_session
from models import Batch, TelemetryChunk
from security import verify_signature
from telemetry_store import insert_points

router = APIRouter(tags=["telemetry-v2"])

_MAX_VALUES = 720
_FUTURE_SKEW_S = 300


class TelemetryChunkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: str = Field(..., max_length=64)
    channel: Literal["T1", "T2", "T3", "T4", "LOAD"]
    t_start: str = Field(..., max_length=64)
    sample_period_s: float = Field(..., ge=1.0, le=60.0)
    values: list[float] = Field(..., min_length=1, max_length=_MAX_VALUES)

    @field_validator("values")
    @classmethod
    def _finite(cls, v: list[float]) -> list[float]:
        if any(not math.isfinite(x) for x in v):
            raise ValueError("values must all be finite")
        return v


def _parse_ts(s: str) -> datetime:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=422, detail="bad t_start")
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


@router.post("/api/v2/telemetry/ingest")
async def ingest(
    payload: TelemetryChunkIn,
    request: Request,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    t_start = _parse_ts(payload.t_start)
    # audit A5: only a FUTURE t_start is impossible. A far-past t_end is NORMAL
    # (72 h offline ring-buffer backfill) and must never be rejected.
    if t_start > datetime.now(timezone.utc) + timedelta(seconds=_FUTURE_SKEW_S):
        raise HTTPException(status_code=422, detail="t_start is in the future")

    exists = (
        await session.execute(
            select(Batch.id).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="unknown batch")

    period = payload.sample_period_s
    n = len(payload.values)
    t_end = t_start + timedelta(seconds=period * (n - 1))

    chunk = TelemetryChunk(
        batch_uuid=payload.batch_uuid,
        device_id=device_id,
        channel=payload.channel,
        t_start=t_start,
        t_end=t_end,
        sample_period_s=period,
        payload_json=json.dumps(payload.model_dump(mode="json")),
        signature=request.headers.get("X-Signature", ""),
    )
    session.add(chunk)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return {"status": "duplicate"}  # idempotent re-ingest, not an error

    rows = [
        {
            "batch_uuid": payload.batch_uuid,
            "channel": payload.channel,
            "ts": t_start + timedelta(seconds=period * i),
            "value": payload.values[i],
        }
        for i in range(n)
    ]
    inserted = await insert_points(session, rows)
    await session.commit()

    telemetry_bus.publish(
        payload.batch_uuid,
        {
            "type": "telemetry",
            "channel": payload.channel,
            "t_start": t_start.isoformat(),
            "sample_period_s": period,
            "values": payload.values,
        },
    )
    return {"status": "ok", "points": inserted}
