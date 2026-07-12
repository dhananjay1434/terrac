from __future__ import annotations
from settings import log
import hmac
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch
from schemas import LabHCorgRequest, LabResultsRequest
from settings import _ADMIN_SECRET
from credit_engine import recompute_batch_credit
from services.lab import apply_lab_results

router = APIRouter()

@router.post("/api/v1/admin/lab-hcorg", status_code=status.HTTP_200_OK)
async def ingest_lab_hcorg(
    payload: LabHCorgRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Authenticated lab channel for the permanence ratio (Phase 8-R).

    A lab-measured H:Corg is authoritative and must NOT be self-asserted by the
    device — it arrives here, admin-authenticated and range-checked, then triggers
    a recompute that can clear the batch's PROVISIONAL status.
    """
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    batch = (
        await session.execute(
            select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown_batch"
        )
    await recompute_batch_credit(session, batch, lab_h_corg=payload.lab_h_corg)
    await session.commit()
    return {
        "status": "ok",
        "batch_uuid": str(payload.batch_uuid),
        "provisional": batch.provisional,
    }
@router.post("/api/v1/admin/lab", status_code=status.HTTP_200_OK)
async def ingest_lab_results(
    payload: LabResultsRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """C7 full lab-results channel (admin-authenticated).

    Widens the Phase-8-R /admin/lab-hcorg endpoint to the full per-batch lab set.
    `organic_carbon_pct` is authoritative and REPLACES the species CORG_TABLE
    constant in the credit (its absence keeps the batch provisional via
    `assumed_corg`, mirroring `assumed_h_corg`). The remaining fields are captured
    for verification / the 1000-year pathway (gated to C8). Lab data must NEVER be
    device-asserted — same admin-secret + range-check discipline as lab-hcorg.
    """
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
    batch = (
        await session.execute(
            select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
        )
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="unknown_batch"
        )

    # P2.4: the portal lab flow (session-authed) is now the primary channel;
    # this X-Admin-Secret endpoint stays for compatibility.
    log.warning(
        "[deprecated] /api/v1/admin/lab — prefer the portal "
        "POST /api/v1/portal/batches/{uuid}/lab-results (P2.4)"
    )
    await apply_lab_results(
        session,
        batch,
        lab_h_corg=payload.lab_h_corg,
        organic_carbon_pct=payload.organic_carbon_pct,
        biochar_moisture_samples=payload.biochar_moisture_samples,
        dry_bulk_density=payload.dry_bulk_density,
        inertinite_pct=payload.inertinite_pct,
        residual_corg_pct=payload.residual_corg_pct,
        ro_measurements_count=payload.ro_measurements_count,
    )
    await session.commit()
    return {
        "status": "ok",
        "batch_uuid": str(payload.batch_uuid),
        "provisional": batch.provisional,
    }
