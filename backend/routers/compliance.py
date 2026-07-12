from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch
from security import _require_admin
from services.compliance import compliance_view

router = APIRouter()

@router.get("/api/v1/batches/{batch_uuid}/compliance")
async def batch_compliance(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    """C10 unified compliance report for a batch (admin).

    Returns the ordered provisional reasons plus a human checklist mapping every
    methodology item to pass/fail, so a Project Developer sees exactly what is
    missing before issuance. `issuable` mirrors `not provisional`.
    """
    _require_admin(x_admin_secret)
    try:
        buid = uuid.UUID(batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")

    return compliance_view(batch)
