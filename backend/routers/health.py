from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch
import observability
import server_signing

router = APIRouter()

# ==================== Endpoints ====================\n
@router.get("/api/health")
async def health(session: AsyncSession = Depends(get_session)) -> JSONResponse:
    # T2.6: probe the DB so a monitor gets a truthful signal (was a static "ok").
    db_ok = True
    try:
        await session.execute(select(1))
    except Exception:  # noqa: BLE001 — health must report, never raise
        db_ok = False
    body = {
        "status": "ok" if db_ok else "degraded",
        "service": "dmrv-api",
        "db": "ok" if db_ok else "down",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(
        body,
        status_code=status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE,
    )
@router.get("/api/v1/pubkeys")
async def pubkeys() -> dict:
    """V8 Part 0.1 — public verify-set for server-signed artifacts.

    Public by design (these are public keys). Server signing is dormant until
    a feature (Part 0.4 remote config, Part 1 field-walk link) enables it, so
    absent config is reported as signing_configured=false rather than a 500 —
    a client checking this before either feature ships must degrade cleanly.
    """
    try:
        keys = server_signing.public_keys()
        current = server_signing.current_kid()
    except RuntimeError:
        return {"signing_configured": False, "current_kid": None, "keys": {}}
    return {"signing_configured": True, "current_kid": current, "keys": keys}


@router.get("/metrics")
async def metrics(
    x_metrics_token: Optional[str] = Header(None, alias="X-Metrics-Token"),
    session: AsyncSession = Depends(get_session),
):
    """Prometheus exposition. P3.4: guarded by DMRV_METRICS_TOKEN (a public
    scrape leaks operational intel). The provisional-ratio gauge is refreshed at
    scrape time from a cheap COUNT so it never drifts."""
    observability.require_metrics_token(x_metrics_token)  # 401 if missing/wrong
    if observability.metrics_enabled():
        total = (
            await session.execute(select(func.count()).select_from(Batch))
        ).scalar() or 0
        prov = (
            await session.execute(
                select(func.count()).select_from(Batch).where(Batch.provisional.is_(True))
            )
        ).scalar() or 0
        observability.set_provisional_ratio((prov / total) if total else 0.0)
    return observability.metrics_payload()
