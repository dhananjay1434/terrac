"""Export endpoints for CSI and Rainbow registries (admin-only)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Batch
from security import _require_admin
from services.export import CSIExportService, RainbowExportService
from settings import log

router = APIRouter()


async def _load_exportable_batch(session: AsyncSession, batch_uuid: str) -> Batch:
    try:
        buid = str(UUID(batch_uuid))
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")

    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()

    if batch is None:
        raise HTTPException(status_code=404, detail="batch_not_found")

    if batch.provisional:
        # Parse the JSON TEXT column so clients get a list, not a raw string
        # (mirrors the portal export route).
        reasons = batch.provisional_reasons
        try:
            parsed = json.loads(reasons) if reasons else []
        except (ValueError, TypeError):
            parsed = []
        raise HTTPException(
            status_code=400,
            detail={
                "error": "batch_is_provisional",
                "reasons": parsed,
                "message": "Batch cannot be exported until all compliance gaps are resolved.",
            },
        )
    return batch


@router.get("/api/v1/batches/{batch_uuid}/export/csi")
async def export_batch_csi(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Export a batch as CSI GlobalCSinkVerificationReport (issuable + admin only)."""
    _require_admin(x_admin_secret)
    batch = await _load_exportable_batch(session, batch_uuid)
    try:
        report = await CSIExportService.export_batch_as_csi(batch, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    report["exported_at"] = datetime.now(timezone.utc).isoformat()
    log.info(f"[export/csi] exported batch {batch.batch_uuid}")
    return report


@router.get("/api/v1/batches/{batch_uuid}/export/rainbow")
async def export_batch_rainbow(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """Export a batch in Rainbow Biochar Standard format (issuable + admin only)."""
    _require_admin(x_admin_secret)
    batch = await _load_exportable_batch(session, batch_uuid)
    try:
        report = await RainbowExportService.export_batch_as_rainbow(batch, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    report["exported_at"] = datetime.now(timezone.utc).isoformat()
    log.info(f"[export/rainbow] exported batch {batch.batch_uuid}")
    return report
