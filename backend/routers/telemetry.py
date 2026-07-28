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
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import telemetry_bus
from db import get_session
from models import Batch, TelemetryChunk, BurnSession, AuditEvent, PortalUser
from portal.auth import require_role
from security import verify_signature, verify_raw_signature
from telemetry_store import insert_points

router = APIRouter(tags=["telemetry-v2"])

_MAX_VALUES = 720
_FUTURE_SKEW_S = 300
_REPLAY_BATCH = 5000  # G3: cap points held in memory per insert during bind


class TelemetryChunkIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    device_id: str = Field(..., max_length=255)
    session_uuid: str = Field(..., max_length=64)
    batch_uuid: str | None = Field(None, max_length=64)
    channel: Literal["T1", "T2", "T3", "T4", "LOAD"]
    t_start: str = Field(..., max_length=64)
    sample_period_s: float = Field(..., ge=1.0, le=60.0)
    values: list[float] = Field(..., min_length=1, max_length=_MAX_VALUES)
    seq: int | None = Field(None)
    prev_hash: str | None = Field(None, max_length=64)
    producer_signature: str = Field(..., max_length=128)

    @field_validator("values")
    @classmethod
    def _finite(cls, v: list[float]) -> list[float]:
        if any(not math.isfinite(x) for x in v):
            raise ValueError("values must all be finite")
        return v

    def canonical_bytes(self) -> bytes:
        d = self.model_dump(exclude={"producer_signature"}, mode="json")
        return json.dumps(d, separators=(",", ":"), sort_keys=True).encode("utf-8")


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
    courier_device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    await verify_raw_signature(
        payload.device_id, payload.producer_signature, payload.canonical_bytes(), session
    )

    t_start = _parse_ts(payload.t_start)
    # audit A5: only a FUTURE t_start is impossible. A far-past t_end is NORMAL
    if t_start > datetime.now(timezone.utc) + timedelta(seconds=_FUTURE_SKEW_S):
        raise HTTPException(status_code=422, detail="t_start is in the future")

    if payload.batch_uuid:
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

    # M2.9 - UPSERT BurnSession
    dialect = session.bind.dialect.name
    insert_stmt = (pg_insert if dialect == "postgresql" else sqlite_insert)(BurnSession).values(
        session_uuid=payload.session_uuid,
        device_id=payload.device_id,
        started_at=t_start,
        batch_uuid=payload.batch_uuid,
    )
    if payload.batch_uuid:
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["session_uuid"],
            set_={"batch_uuid": insert_stmt.excluded.batch_uuid}
        )
    else:
        upsert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["session_uuid"])
    await session.execute(upsert_stmt)

    chunk = TelemetryChunk(
        session_uuid=payload.session_uuid,
        batch_uuid=payload.batch_uuid,
        device_id=payload.device_id,
        courier_device_id=courier_device_id,
        channel=payload.channel,
        t_start=t_start,
        t_end=t_end,
        sample_period_s=period,
        seq=payload.seq,
        prev_hash=payload.prev_hash,
        payload_json=json.dumps(payload.model_dump(mode="json")),
        signature=payload.producer_signature,
    )
    session.add(chunk)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        return {"status": "duplicate"}  # idempotent re-ingest, not an error

    inserted = 0
    if payload.batch_uuid:
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

    # Publish to SSE bus only if bound (since it relies on batch_uuid)
    if payload.batch_uuid:
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


class BindSessionRequest(BaseModel):
    batch_uuid: str = Field(..., max_length=64)


@router.post("/api/v2/telemetry/sessions/{session_uuid}/bind")
async def bind_session(
    session_uuid: str,
    payload: BindSessionRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    # 1. Verify BurnSession exists
    burn_session = (
        await session.execute(
            select(BurnSession).where(BurnSession.session_uuid == session_uuid)
        )
    ).scalar_one_or_none()
    
    if not burn_session:
        raise HTTPException(status_code=404, detail="session_not_found")
        
    if burn_session.batch_uuid == payload.batch_uuid:
        return {"status": "ok", "points_inserted": 0, "message": "already_bound"}

    # 2. Verify target Batch exists
    batch_exists = (
        await session.execute(
            select(Batch.id).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if not batch_exists:
        raise HTTPException(status_code=404, detail="batch_not_found")

    # 3. Update BurnSession
    burn_session.batch_uuid = payload.batch_uuid
    burn_session.binding_source = "admin"
    burn_session.bound_by = user.email
    burn_session.bound_at = datetime.now(timezone.utc)

    # 4. Update TelemetryChunks
    await session.execute(
        update(TelemetryChunk)
        .where(TelemetryChunk.session_uuid == session_uuid)
        .where(TelemetryChunk.batch_uuid.is_(None))
        .values(batch_uuid=payload.batch_uuid)
    )
    await session.flush()

    # 5. Extract points from chunks and insert, in bounded batches (G3).
    #    A 72 h offline backfill is normal, so the full point set can be ~10^5 rows
    #    - never materialise it all at once. A chunk with corrupt payload_json is
    #    skipped and counted, not fatal: partial recovery beats losing a burn.
    chunks = (
        await session.execute(
            select(TelemetryChunk).where(TelemetryChunk.session_uuid == session_uuid)
        )
    ).scalars().all()

    points_inserted = 0
    skipped_chunks = 0
    rows: list[dict] = []
    for chunk in chunks:
        try:
            chunk_payload = json.loads(chunk.payload_json)
            values = chunk_payload.get("values", [])
        except (ValueError, TypeError):
            skipped_chunks += 1
            continue
        period = chunk.sample_period_s
        for i, val in enumerate(values):
            rows.append({
                "batch_uuid": payload.batch_uuid,
                "channel": chunk.channel,
                "ts": chunk.t_start + timedelta(seconds=period * i),
                "value": val,
            })
            if len(rows) >= _REPLAY_BATCH:
                points_inserted += await insert_points(session, rows)
                rows = []
    if rows:
        points_inserted += await insert_points(session, rows)

    # 6. Write AuditEvent
    session.add(
        AuditEvent(
            event_type="session_bound",
            batch_uuid=payload.batch_uuid,
            payload_json=json.dumps(
                {"session_uuid": session_uuid, "bound_by": user.email}
            ),
        )
    )

    await session.commit()
    return {
        "status": "ok",
        "points_inserted": points_inserted,
        "skipped_chunks": skipped_chunks,
    }
