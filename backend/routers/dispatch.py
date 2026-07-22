"""V8 Part 3.3 — device-signed dispatch endpoints (custody transfer).

Create (draft, idempotent upsert while still draft) and transition
(draft -> in_transit -> received). Ownership: only the device that created a
dispatch may transition it (mirrors _assert_batch_ownership's "owned by a
different device -> 403" rule). All status-machine rules (legal transitions,
weight-lock, dual-weigh reconciliation) live in services/dispatch_state.py —
this router is the thin DB edge that calls them and persists the result.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

import observability
import settings
from db import get_session
from models import Dispatch, DispatchSite, Facility
from schemas import DispatchCreate, DispatchTransition
from security import verify_signature
from services import dispatch_state as ds

router = APIRouter()


@router.get("/api/v1/facilities")
async def list_facilities_for_device(
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """V8 Part 3.4 — device-facing list of ACTIVE facilities, so the field app
    can let the operator pick a dispatch's destination by name instead of
    pasting a raw UUID (mirrors GET /api/v1/parcels for source parcels).
    Read-only; returns only what the picker needs."""
    rows = (
        (
            await session.execute(
                select(Facility).where(Facility.status == "active")
            )
        )
        .scalars()
        .all()
    )
    return {
        "facilities": [
            {"facility_uuid": f.facility_uuid, "name": f.name, "facility_type": f.facility_type}
            for f in rows
        ]
    }


@router.post(
    "/api/v1/dispatch",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_dispatch(
    payload: DispatchCreate,
    response: Response,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    existing = (
        await session.execute(
            select(Dispatch).where(Dispatch.dispatch_uuid == payload.dispatch_uuid)
        )
    ).scalar_one_or_none()

    if existing is not None:
        if existing.device_id != device_id:
            raise HTTPException(status_code=403, detail="not_your_dispatch")
        if existing.status != "draft":
            # Weight-lock / sequential-stage gating: once a dispatch has left
            # draft, re-POSTing it (which would edit weight_source_kg) is
            # rejected outright — only /transition may move it forward.
            raise HTTPException(status_code=409, detail="dispatch_locked")
        dispatch = existing
        response.status_code = status.HTTP_200_OK
    else:
        dispatch = Dispatch(dispatch_uuid=payload.dispatch_uuid, device_id=device_id)
        session.add(dispatch)

    dispatch.kind = payload.kind
    dispatch.source_ref = payload.source_ref
    dispatch.dest_facility_uuid = payload.dest_facility_uuid
    dispatch.weight_source_kg = payload.weight_source_kg
    dispatch.weight_source_method = payload.weight_source_method
    dispatch.driver_name = payload.driver_name
    dispatch.driver_phone = payload.driver_phone
    dispatch.truck_number = payload.truck_number

    await session.execute(
        delete(DispatchSite).where(DispatchSite.dispatch_uuid == payload.dispatch_uuid)
    )
    for site in payload.sites:
        session.add(
            DispatchSite(
                dispatch_uuid=payload.dispatch_uuid,
                parcel_uuid=site.parcel_uuid,
                moisture_pct=site.moisture_pct,
                truck_percentage_filled=site.truck_percentage_filled,
            )
        )

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="dispatch_conflict")

    return {
        "status": "success",
        "dispatch_uuid": dispatch.dispatch_uuid,
        "dispatch_status": dispatch.status,
    }


@router.get("/api/v1/dispatch/{dispatch_uuid}")
async def get_dispatch_status(
    dispatch_uuid: str,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Deferred R2 — device-facing status read, so a resumed wizard can
    reconcile its persisted phase against server truth instead of trusting a
    possibly-stale local value. Same ownership rule as `transition_dispatch`.
    404 (not the 200-with-null pattern used elsewhere) is correct here: the
    app only calls this for a dispatch_uuid IT persisted locally, so a 404
    unambiguously means "the draft never reached the server" — the caller
    already knows to treat that as "resume to draft, nothing to reconcile."
    """
    dispatch = (
        await session.execute(
            select(Dispatch).where(Dispatch.dispatch_uuid == dispatch_uuid)
        )
    ).scalar_one_or_none()
    if dispatch is None:
        raise HTTPException(status_code=404, detail="dispatch_not_found")
    if dispatch.device_id != device_id:
        raise HTTPException(status_code=403, detail="not_your_dispatch")
    return {"dispatch_uuid": dispatch.dispatch_uuid, "status": dispatch.status}


@router.post("/api/v1/dispatch/{dispatch_uuid}/transition")
async def transition_dispatch(
    dispatch_uuid: str,
    payload: DispatchTransition,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    dispatch = (
        await session.execute(
            select(Dispatch).where(Dispatch.dispatch_uuid == dispatch_uuid)
        )
    ).scalar_one_or_none()
    if dispatch is None:
        raise HTTPException(status_code=404, detail="dispatch_not_found")
    if dispatch.device_id != device_id:
        raise HTTPException(status_code=403, detail="not_your_dispatch")

    try:
        ds.validate_transition(dispatch.status, payload.target_status)
    except ds.IllegalTransitionError as exc:
        raise HTTPException(
            status_code=409, detail={"code": "illegal_transition", "message": str(exc)}
        )

    now = datetime.now(timezone.utc)

    if payload.target_status == "in_transit":
        if not dispatch.weight_source_kg or dispatch.weight_source_kg <= 0:
            raise HTTPException(status_code=422, detail="missing_weight_source")
        dispatch.status = "in_transit"
        dispatch.transitioned_at = now

    elif payload.target_status == "received":
        if payload.weight_facility_kg is None:
            raise HTTPException(status_code=422, detail="missing_weight_facility")
        result = ds.reconcile_dual_weight(
            weight_source_kg=dispatch.weight_source_kg or 0.0,
            weight_facility_kg=payload.weight_facility_kg,
            tolerance_pct=settings.dispatch_weight_tolerance_pct(),
        )
        dispatch.weight_facility_kg = payload.weight_facility_kg
        dispatch.weight_delta_kg = result.delta_kg
        dispatch.weight_delta_pct = result.delta_pct
        dispatch.weight_flagged = result.flagged
        dispatch.status = "received"
        dispatch.received_at = now
        if result.flagged:
            observability.record_gate_rejection(
                gate="dispatch_reconciliation",
                reason=result.reason or "weight_discrepancy",
                extra={
                    "dispatch_uuid": dispatch_uuid,
                    "delta_pct": result.delta_pct,
                },
            )

    await session.commit()
    return {
        "status": "success",
        "dispatch_uuid": dispatch_uuid,
        "dispatch_status": dispatch.status,
        "weight_flagged": dispatch.weight_flagged,
        "weight_delta_pct": dispatch.weight_delta_pct,
    }
