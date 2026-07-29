"""Portal Stage Timeline API (M3.2)."""

import json
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import (
    Batch,
    BatchStageEvent,
    EndUseApplication,
    MediaFile,
    PyrolysisTelemetry,
    PortalUser,
)
from portal.auth import require_role
from feature_flags import flag_active
from models import Project
from stage_projection import STAGE_ORDER

router = APIRouter(prefix="/api/v1/portal", tags=["portal", "timeline"])

# Mapping from provisional_reasons tokens to the stage they block.
# This powers the `blocking: true` flag on empty stages.
_PROVISIONAL_REASON_TO_STAGE = {
    "missing_post_burn_mass": "yield",
    "missing_end_use": "application",
    "min_temp_uncorroborated": "firing",
    "assumed_h_corg": "lab",
    "assumed_corg": "lab",
    "missing_moisture": "moisture",
    "missing_dispatch": "dispatch",
}


@router.get("/batches/{batch_uuid}/timeline")
async def get_batch_timeline(
    batch_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    try:
        buid = str(_uuid.UUID(batch_uuid))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")

    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="unknown_batch")

    # R4: timeline is an opt-out display feature. If a client turned it off, hide it
    # (empty list -> the portal renders no timeline panel). Default is ON.
    _org = None
    if batch.project_id:
        _proj = (
            await session.execute(select(Project).where(Project.project_id == batch.project_id))
        ).scalar_one_or_none()
        _org = _proj.org_id if _proj else None
    if not await flag_active(session, "timeline_v2", _org):
        return []

    reasons = []
    try:
        reasons = json.loads(batch.provisional_reasons or "[]")
    except (json.JSONDecodeError, TypeError):
        pass
    blocking_stages = {_PROVISIONAL_REASON_TO_STAGE.get(r) for r in reasons if r in _PROVISIONAL_REASON_TO_STAGE}

    # Load actual stage events
    events = (
        await session.execute(
            select(BatchStageEvent).where(BatchStageEvent.batch_uuid == buid)
        )
    ).scalars().all()
    events_by_stage = {e.stage: e for e in events}

    # Load media to attach to stages
    from stage_projection import _stage_for_capture

    media_rows = (
        await session.execute(
            select(MediaFile)
            .where(MediaFile.batch_uuid == buid)
            .order_by(MediaFile.uploaded_at.asc())
        )
    ).scalars().all()
    
    media_by_stage = {s: [] for s in STAGE_ORDER}
    for m in media_rows:
        stage = _stage_for_capture(m.capture_type)
        if stage and stage in media_by_stage:
            media_by_stage[stage].append({
                "operation_id": m.operation_id,
                "filename": m.filename,
                "sha256_hash": m.sha256_hash,
                "capture_type": m.capture_type,
                "capture_type_verified": bool(m.capture_type_verified),
                "exif_lat": m.exif_lat,
                "exif_lon": m.exif_lon,
                "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
                "verification_status": m.verification_status,
                "verification_remarks": m.verification_remarks,
            })

    # Load telemetry summary for firing stage
    tel = (
        await session.execute(
            select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == buid)
        )
    ).scalar_one_or_none()
    
    tel_summary = None
    if tel:
        try:
            payload = json.loads(tel.payload_json or "{}")
            # R4: canonical key is temperature_readings (list of floats), per
            # corroboration.py / credit_engine.py. The old temperatureReadingsJson
            # + r.get("temperature") never matched real data -> max_temp always None.
            t_readings = payload.get("temperature_readings", []) or []
            numeric = [float(r) for r in t_readings if isinstance(r, (int, float))]
            max_temp = max(numeric) if numeric else None
                
            tel_summary = {
                "max_temp": max_temp,
                "duration_min": round(batch.harvest_uptime_seconds / 60) if batch.harvest_uptime_seconds else None
            }
        except Exception:
            pass

    timeline = []
    for stage_name in STAGE_ORDER:
        event = events_by_stage.get(stage_name)
        stage_media = media_by_stage.get(stage_name, [])
        
        if event:
            state = "done" if event.ended_at else "active"
            started = event.started_at.isoformat() if event.started_at else None
            ended = event.ended_at.isoformat() if event.ended_at else None
        else:
            state = "empty"
            started = None
            ended = None

        node = {
            "stage": stage_name,
            "state": state,
            "started_at": started,
            "ended_at": ended,
            "media": stage_media,
        }
        
        if state == "empty" and stage_name in blocking_stages:
            node["blocking"] = True
            
        if stage_name == "firing" and tel_summary:
            node["telemetry_summary"] = tel_summary

        timeline.append(node)

    return timeline
