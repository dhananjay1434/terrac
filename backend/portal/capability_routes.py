"""R4 - per-batch capability descriptor. The portal renders panels from this
verdict instead of probing endpoints and guessing."""
import uuid as _uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Batch, PortalUser
from portal.auth import require_role
from capabilities import resolve_batch_capabilities

router = APIRouter(prefix="/api/v1/portal", tags=["portal", "capabilities"])


@router.get("/batches/{batch_uuid}/capabilities")
async def get_batch_capabilities(
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
    return await resolve_batch_capabilities(session, batch)
