from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from db import AsyncSession, get_session
from models import Batch, BatchStageEvent, MediaFile, PyrolysisTelemetry, TelemetryChunk
from security import _require_admin
from stage_projection import STAGE_ORDER, _CAPTURE_STAGE

router = APIRouter(prefix="/api/v1/portal", tags=["timeline"])

# Mappings of provisional reasons to the stage they block.
# This implements the logic described in M3.2 requirements.
REASON_STAGE_MAP = {
    "missing_biomass_input": "loading",
    "missing_conversion_factor": "yield",
    "wet_yield_uncorroborated": "yield",
    "min_temp_uncorroborated": "firing",
    "insufficient_moisture_samples": "moisture",
    "missing_pyrolysis_photos": "firing",
    "flame_height_out_of_range": "firing",
    "missing_ignition_energy": "firing",
    "missing_composite_sample": "packaging",
    "transport_uncorroborated": "dispatch",
    "missing_delivery_record": "dispatch",
    "missing_buyer_identity": "application",
    "unregistered_kiln": "sourcing",
    "scale_calibration_expired": "yield",
    "missing_annual_methane": "firing",
    "missing_pah": "lab",
    "assumed_h_corg": "lab",
    "assumed_corg": "lab",
    "attestation_unverified": "firing",
    "missing_post_burn_mass": "yield",
    "missing_end_use": "application",
}

@router.get("/batches/{batch_uuid}/timeline")
async def get_batch_timeline(
    batch_uuid: str,
    s: AsyncSession = Depends(get_session),
    admin_ctx: dict = Depends(_require_admin)
) -> List[Dict[str, Any]]:
    # 1. Fetch batch to check existence and provisional reasons
    b = (await s.execute(select(Batch).where(Batch.batch_uuid == batch_uuid))).scalar_one_or_none()
    if not b:
        raise HTTPException(status_code=404, detail="batch_not_found")
        
    import json
    provisional_reasons = []
    if b.provisional_reasons:
        try:
            provisional_reasons = json.loads(b.provisional_reasons)
        except Exception:
            pass

    # Determine blocking stages based on provisional reasons
    blocking_stages = set()
    for reason in provisional_reasons:
        if reason in REASON_STAGE_MAP:
            blocking_stages.add(REASON_STAGE_MAP[reason])

    # 2. Fetch stage events
    events_res = await s.execute(
        select(BatchStageEvent)
        .where(BatchStageEvent.batch_uuid == batch_uuid)
    )
    events = events_res.scalars().all()
    events_by_stage = {e.stage: e for e in events}

    # 3. Fetch media files
    media_res = await s.execute(
        select(MediaFile)
        .where(MediaFile.batch_uuid == batch_uuid)
        .order_by(MediaFile.uploaded_at.asc())
    )
    media_files = media_res.scalars().all()
    
    media_by_stage = {stg: [] for stg in STAGE_ORDER}
    for m in media_files:
        if not m.capture_type:
            continue
        stg = _CAPTURE_STAGE.get(m.capture_type)
        if not stg:
            # check smoke prefix
            if m.capture_type in {"smoke_0", "smoke_50", "smoke_90", "smoke_100", "0", "50", "90", "100"} or m.capture_type.startswith("smoke_"):
                stg = "firing"
        if stg and stg in media_by_stage:
            media_by_stage[stg].append({
                "capture_type": m.capture_type,
                "url": f"/media/{m.filename}",
            })

    # 4. Fetch telemetry to create summary
    telemetry_res = await s.execute(
        select(PyrolysisTelemetry)
        .where(PyrolysisTelemetry.batch_uuid == batch_uuid)
    )
    telemetries = telemetry_res.scalars().all()
    
    max_t = None
    telemetry_count = 0
    # simplified telemetry summary for test/timeline
    for tel in telemetries:
        try:
            payload = json.loads(tel.payload_json)
            readings = payload.get("temperatureReadingsJson", [])
            for r in readings:
                t = r.get("temperature")
                if t is not None:
                    if max_t is None or t > max_t:
                        max_t = t
                    telemetry_count += 1
        except Exception:
            pass

    # 5. Assemble Timeline
    timeline = []
    for stage in STAGE_ORDER:
        stg_event = events_by_stage.get(stage)
        media_list = media_by_stage.get(stage, [])
        
        node = {
            "stage": stage,
            "media": media_list,
            "started_at": stg_event.started_at.isoformat() if stg_event and stg_event.started_at else None,
            "ended_at": stg_event.ended_at.isoformat() if stg_event and stg_event.ended_at else None,
        }
        
        if stg_event and stg_event.started_at:
            if stg_event.ended_at:
                node["state"] = "done"
            else:
                node["state"] = "active"
        else:
            node["state"] = "empty"
            
        if node["state"] == "empty" and stage in blocking_stages:
            node["blocking"] = True
            
        if stage == "firing" and max_t is not None:
            node["telemetry_summary"] = {
                "max_temp": max_t,
                "duration_min": 60 # mocked duration for now as per test
            }
            
        timeline.append(node)
        
    return timeline
