"""PR-5.1a — device-signed day-start audit endpoint.

The prerequisite server-side record for day-start evidence media: R6
shipped the attestation client-only (SharedPreferences), so there was no
subject_uuid to attach media to. This is the thin DB edge; the natural key
(facility_uuid, audit_date) is enforced by a DB unique constraint — mirrors
routers/dispatch.py's create_dispatch idempotent-upsert shape.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, Response, status

from db import get_session
from models import DayStartAudit
from schemas import DayStartAuditCreate
from security import verify_signature

router = APIRouter()


@router.post(
    "/api/v1/day-start-audits",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def create_day_start_audit(
    payload: DayStartAuditCreate,
    response: Response,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
):
    existing_by_uuid = (
        await session.execute(
            select(DayStartAudit).where(DayStartAudit.audit_uuid == payload.audit_uuid)
        )
    ).scalar_one_or_none()

    if existing_by_uuid is not None:
        if existing_by_uuid.device_id != device_id:
            raise HTTPException(status_code=403, detail="not_your_day_start_audit")
        response.status_code = status.HTTP_200_OK
        return {
            "status": "success",
            "audit_uuid": existing_by_uuid.audit_uuid,
            "facility_uuid": existing_by_uuid.facility_uuid,
            "audit_date": existing_by_uuid.audit_date,
        }

    audit = DayStartAudit(
        audit_uuid=payload.audit_uuid,
        facility_uuid=payload.facility_uuid,
        audit_date=payload.audit_date,
        device_id=device_id,
    )
    session.add(audit)
    try:
        await session.commit()
    except IntegrityError:
        # The natural key (facility_uuid, audit_date) is already claimed —
        # by this device under a different audit_uuid, or by another device.
        # Either way this specific audit_uuid did not win the slot: 409.
        await session.rollback()
        raise HTTPException(status_code=409, detail="day_start_audit_conflict")

    return {
        "status": "success",
        "audit_uuid": audit.audit_uuid,
        "facility_uuid": audit.facility_uuid,
        "audit_date": audit.audit_date,
    }
