"""Deferred R3 — device-signed bulk-density calibration submission.

F's existing bulk-density-tests route (`portal/routes.py::create_bulk_density_test`)
is admin/portal-only (`require_role("admin")`) and trusts a client-supplied
`density_kg_per_l` directly — a field device (Ed25519-signed, no admin
password) cannot call it, and it isn't server-computed. This endpoint closes
that gap for the field-capture path: device-signed, idempotent create
(mirrors `routers/dispatch.py`'s create_dispatch), and the density is always
computed server-side from the submitted mass/volume.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import BulkDensityTest
from schemas import DensityTestSubmit
from security import verify_signature
from services.bulk_density import mass_and_volume_to_density_kg_per_l

router = APIRouter()


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid_datetime")


@router.post("/api/v1/density-tests", status_code=status.HTTP_201_CREATED)
async def submit_density_test(
    payload: DensityTestSubmit,
    device_id: str = Depends(verify_signature),
    session: AsyncSession = Depends(get_session),
) -> dict:
    existing = (
        await session.execute(
            select(BulkDensityTest).where(
                BulkDensityTest.test_uuid == payload.test_uuid
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        # Idempotent re-POST of the same test_uuid: a no-op, not a second row
        # (the outbox/direct-call retry contract every entity endpoint here
        # follows). Return the already-stored, server-computed density.
        return {
            "test_uuid": existing.test_uuid,
            "density_kg_per_l": existing.density_kg_per_l,
        }

    try:
        density_kg_per_l = mass_and_volume_to_density_kg_per_l(
            payload.mass_kg, payload.volume_l
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"invalid_density_inputs: {exc}")

    performed_at = (
        _parse_dt(payload.performed_at) if payload.performed_at else None
    )

    test = BulkDensityTest(
        test_uuid=payload.test_uuid,
        project_id=payload.project_id,
        density_kg_per_l=density_kg_per_l,
        performed_at=performed_at or datetime.now(timezone.utc),
        mass_kg=payload.mass_kg,
        volume_l=payload.volume_l,
        # Deferred R3 scope: no field-capture UX yet for setting an explicit
        # calibration expiry — valid_until stays NULL (the production_
        # requires_valid_density gate treats NULL as "not in date", the same
        # fail-closed default the admin-portal create path already has).
        valid_until=None,
    )
    session.add(test)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=409, detail="bulk_density_test_already_exists"
        )
    await session.commit()

    return {"test_uuid": test.test_uuid, "density_kg_per_l": test.density_kg_per_l}
