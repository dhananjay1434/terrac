"""Portal telemetry read API (M2.3) + live SSE stream shell (M2.4).

M2.3 — GET /api/v1/portal/batches/{uuid}/telemetry2?channels=&res=10s|1m
  Response shape is the api2.ts/ThermalMapChart contract: point timestamps are
  EPOCH MILLISECONDS; gaps are computed, never interpolated (audit A4).
  res=1m aggregates in Python rather than SQL — portable across SQLite/Postgres
  and trivially fast at burn scale (a 4 h burn is ~1,440 raw points/channel);
  the persisted telemetry_rollup_1m table is deferred to the M6.2 perf pass,
  which will measure whether it is needed at all (documented deviation).

M2.4 — POST .../streams/burn/{uuid}/ticket (bearer-auth) mints a single-use
  60 s ticket; GET .../streams/burn/{uuid}?ticket= redeems it and streams
  Server-Sent Events. All pub/sub + ticket logic lives in telemetry_bus
  (audit A8) — this file is deliberately a thin HTTP shell over it.
"""
from __future__ import annotations

import asyncio
import json
from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import telemetry_bus
from db import get_session
from models import Batch, PortalUser, TelemetryPoint, TelemetryChunk
from telemetry_integrity import detect_chain_gaps
from portal.auth import require_role

router = APIRouter(tags=["portal-telemetry"])

_CHANNELS = ("T1", "T2", "T3", "T4", "LOAD")
# a hole larger than 6 sample periods (60 s at the 10 s cadence) is a gap
_GAP_THRESHOLD_MS = 60_000


async def _batch_or_404(session: AsyncSession, uuid: str) -> None:
    exists = (
        await session.execute(select(Batch.id).where(Batch.batch_uuid == uuid))
    ).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=404, detail="unknown batch")


def _minute_rollup(points: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """Mean per 1-minute bucket (epoch-ms in/out, bucket stamped at its start)."""
    if not points:
        return []
    buckets: dict[int, list[float]] = {}
    for ts, v in points:
        buckets.setdefault(ts - ts % 60_000, []).append(v)
    return [(b, sum(vs) / len(vs)) for b, vs in sorted(buckets.items())]


def _find_gaps(sorted_ts: list[int]) -> list[list[int]]:
    gaps: list[list[int]] = []
    for prev, cur in zip(sorted_ts, sorted_ts[1:]):
        if cur - prev > _GAP_THRESHOLD_MS:
            gaps.append([prev, cur])
    return gaps


@router.get("/api/v1/portal/batches/{uuid}/telemetry2")
async def read_telemetry2(
    uuid: str,
    channels: Optional[str] = Query(None, description="CSV subset of T1..T4,LOAD"),
    res: str = Query("10s", pattern="^(10s|1m)$"),
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    await _batch_or_404(session, uuid)

    wanted = [c.strip() for c in channels.split(",")] if channels else list(_CHANNELS)
    bad = [c for c in wanted if c not in _CHANNELS]
    if bad:
        raise HTTPException(status_code=422, detail=f"unknown channels: {bad}")

    rows = (
        await session.execute(
            select(TelemetryPoint.channel, TelemetryPoint.ts, TelemetryPoint.value)
            .where(
                TelemetryPoint.batch_uuid == uuid,
                TelemetryPoint.channel.in_(wanted),
            )
            .order_by(TelemetryPoint.ts)
        )
    ).all()

    by_channel: dict[str, list[tuple[int, float]]] = {}
    for channel, ts, value in rows:
        # SQLite returns naive datetimes even for DateTime(timezone=True); a
        # naive .timestamp() would apply the SERVER's local offset (+05:30 IST
        # → every burn shifted 5.5 h on dev). Values are stored as UTC, so
        # coerce naive → UTC explicitly. Postgres returns aware — no-op there.
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        ms = int(ts.timestamp() * 1000)
        by_channel.setdefault(channel, []).append((ms, float(value)))

    out_channels: dict[str, dict] = {}
    all_ts: list[int] = []
    for channel, pts in by_channel.items():
        if res == "1m":
            pts = _minute_rollup(pts)
        values = [v for _, v in pts]
        out_channels[channel] = {
            "points": [[ts, v] for ts, v in pts],
            "max": max(values),
            "min": min(values),
        }
        all_ts.extend(ts for ts, _ in pts)

    all_ts.sort()
    burn = {
        "t_start": all_ts[0] if all_ts else 0,
        "t_end": all_ts[-1] if all_ts else 0,
        "gaps": _find_gaps(all_ts),
    }
    # R5: annotate (never reject) any chain gap for this batch's chunks so the
    # portal can render deletion/reorder as an evident break.
    chunk_rows = (
        await session.execute(
            select(TelemetryChunk.session_uuid, TelemetryChunk.channel, TelemetryChunk.seq)
            .where(TelemetryChunk.batch_uuid == uuid)
        )
    ).all()
    chain_gaps = detect_chain_gaps(
        [{"session_uuid": s, "channel": c, "seq": q} for (s, c, q) in chunk_rows]
    )
    return {"channels": out_channels, "burn": burn, "chain_gaps": chain_gaps}


# ── M2.4: SSE shell over telemetry_bus (audit A1/A8) ────────────────────────
@router.post("/api/v1/portal/streams/burn/{uuid}/ticket")
async def mint_stream_ticket(
    uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    await _batch_or_404(session, uuid)
    return {"ticket": telemetry_bus.mint_ticket(uuid), "expires_in": int(telemetry_bus.TICKET_TTL_S)}


@router.get("/api/v1/portal/streams/burn/{uuid}")
async def stream_burn(uuid: str, ticket: str = Query(...)):
    # ticket IS the auth here (EventSource cannot send headers — audit A1);
    # single-use + 60 s TTL + batch-bound, minted by the bearer-authed POST.
    if not telemetry_bus.redeem_ticket(ticket, uuid):
        raise HTTPException(status_code=401, detail="invalid or expired ticket")

    async def eventgen():
        q = telemetry_bus.subscribe(uuid)
        try:
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield f"event: telemetry\ndata: {json.dumps(frame)}\n\n"
                except asyncio.TimeoutError:
                    yield ": ping\n\n"  # heartbeat keeps proxies from closing us
        finally:
            telemetry_bus.unsubscribe(uuid, q)

    return StreamingResponse(
        eventgen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
