"""Portal API router.

Mounted once from `server.py` via `app.include_router(router)`. Every new portal
endpoint hangs off THIS router — `server.py` only ever gains the single mount
line. Rate limiting for `/api/v1/portal/*` maps to the "admin" bucket in
`server._rl_bucket`.
"""

import hashlib
import json
import secrets
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Header,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import (
    Batch,
    CompositePileSample,
    DeviceKey,
    EndUseApplication,
    MediaFile,
    MoistureReading,
    PortalUser,
    PyrolysisTelemetry,
    TransportEvent,
    YieldMetrics,
    EnrollmentToken,
)
from .auth import (
    create_session,
    require_role,
    revoke_session,
    verify_login,
)
from .schemas import (
    LabResultsInput,
    LoginRequest,
    LoginResponse,
    MintTokenRequest,
    MintTokenResponse,
)

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])

# Enrollment tokens are minted server-side with 256 bits of entropy — far above
# the ≥128-bit floor (M3). token_urlsafe(n) draws n random bytes.
_ENROLL_TOKEN_BYTES = 32


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    user = (
        await session.execute(
            select(PortalUser).where(PortalUser.email == payload.email)
        )
    ).scalar_one_or_none()

    # A disabled user must never authenticate; feed None so the check still
    # burns one argon2 verify (constant-ish timing) and fails.
    stored = user.password_hash if (user is not None and not user.disabled) else None
    if not verify_login(stored, payload.password):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "invalid_credentials"},
        )

    token, expires = await create_session(session, user.id)
    return LoginResponse(
        token=token, expires_at=expires.isoformat(), role=user.role
    )


@router.post("/logout")
async def logout(
    authorization: str | None = Header(None, alias="Authorization"),
    session: AsyncSession = Depends(get_session),
):
    if authorization and authorization.lower().startswith("bearer "):
        await revoke_session(session, authorization[7:].strip())
    return {"status": "logged_out"}


@router.post(
    "/tokens",
    response_model=MintTokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def mint_enrollment_token(
    payload: MintTokenRequest,
    _admin: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Admin-only: mint a single-use device enrollment token (256-bit) and
    return it plus a scannable QR payload `dmrv-enroll:v1:{...}`."""
    token = secrets.token_urlsafe(_ENROLL_TOKEN_BYTES)
    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    session.add(EnrollmentToken(token=token, expires_at=expires))
    await session.commit()

    qr_payload = "dmrv-enroll:v1:" + json.dumps(
        {"url": payload.base_url or "", "token": token},
        separators=(",", ":"),
    )
    return MintTokenResponse(
        token=token, expires_at=expires.isoformat(), qr_payload=qr_payload
    )


# ---------------------------------------------------------------------------
# P2.2 — Read API (any authenticated portal user). Verifiers read; nobody
# writes here. Media bytes stream through an authed route — no static path
# ever leaves the server.
# ---------------------------------------------------------------------------

_PAGE_MAX = 100


def _batch_row(b: Batch) -> dict:
    reasons = b.provisional_reasons
    try:
        reason_count = len(json.loads(reasons)) if reasons else 0
    except (ValueError, TypeError):
        reason_count = 0
    return {
        "batch_uuid": str(b.batch_uuid),
        "device_id": b.device_id,
        "project_id": b.project_id,
        "status": b.status,
        "provisional": b.provisional,
        "reason_count": reason_count,
        "net_credit_t_co2e": b.net_credit_t_co2e,
        "wet_yield_kg": b.wet_yield_kg,
        "received_at": b.received_at.isoformat() if b.received_at else None,
    }


@router.get("/batches")
async def list_batches(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    status_eq: Optional[str] = Query(None, alias="status"),
    provisional: Optional[bool] = None,
    device_id: Optional[str] = None,
    project_id: Optional[str] = None,
    received_from: Optional[str] = None,
    received_to: Optional[str] = None,
    before: Optional[str] = Query(None, description="cursor: received_at ISO"),
    limit: int = Query(50, ge=1, le=_PAGE_MAX),
):
    stmt = select(Batch)
    if status_eq is not None:
        stmt = stmt.where(Batch.status == status_eq)
    if provisional is not None:
        stmt = stmt.where(Batch.provisional == provisional)
    if device_id is not None:
        stmt = stmt.where(Batch.device_id == device_id)
    if project_id is not None:
        stmt = stmt.where(Batch.project_id == project_id)
    if received_from:
        stmt = stmt.where(Batch.received_at >= _parse_dt(received_from))
    if received_to:
        stmt = stmt.where(Batch.received_at <= _parse_dt(received_to))
    if before:
        stmt = stmt.where(Batch.received_at < _parse_dt(before))
    stmt = stmt.order_by(Batch.received_at.desc(), Batch.id.desc()).limit(limit + 1)

    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = (
        rows[-1].received_at.isoformat() if has_more and rows and rows[-1].received_at
        else None
    )
    return {"batches": [_batch_row(b) for b in rows], "next_cursor": next_cursor}


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="invalid_datetime")


@router.get("/batches/{batch_uuid}")
async def batch_detail(
    batch_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    import uuid as _uuid

    from server import compliance_view  # reuse the ONE grading view (P2.0 coupling)

    try:
        buid = _uuid.UUID(batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")

    key = str(buid)

    async def _count(model, col) -> int:
        return int(
            (await session.execute(select(func.count()).where(col == key))).scalar() or 0
        )

    evidence = {
        "moisture_readings": await _count(MoistureReading, MoistureReading.batch_uuid),
        "composite_pile_samples": await _count(
            CompositePileSample, CompositePileSample.batch_uuid
        ),
        "transport_events": await _count(TransportEvent, TransportEvent.batch_uuid),
        "pyrolysis_telemetry": await _count(
            PyrolysisTelemetry, PyrolysisTelemetry.batch_uuid
        ),
        "yield_metrics": await _count(YieldMetrics, YieldMetrics.batch_uuid),
        "end_use_application": await _count(
            EndUseApplication, EndUseApplication.batch_uuid
        ),
    }

    media_rows = (
        await session.execute(
            select(MediaFile)
            .where(MediaFile.batch_uuid == buid)
            .order_by(MediaFile.uploaded_at.asc())
        )
    ).scalars().all()
    media = [
        {
            "operation_id": m.operation_id,
            "filename": m.filename,
            "sha256_hash": m.sha256_hash,
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
        }
        for m in media_rows
    ]

    return {
        "batch": _batch_row(batch),
        "compliance": compliance_view(batch),
        "evidence_counts": evidence,
        "media": media,
    }


@router.get("/devices")
async def list_devices(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(DeviceKey).order_by(DeviceKey.registered_at.desc())
        )
    ).scalars().all()
    return {
        "devices": [
            {
                "device_id": d.device_id,
                "registered_at": d.registered_at.isoformat()
                if d.registered_at
                else None,
            }
            for d in rows
        ]
    }


@router.get("/summary")
async def summary(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    status_rows = (
        await session.execute(
            select(Batch.status, func.count()).group_by(Batch.status)
        )
    ).all()
    provisional_count = int(
        (
            await session.execute(
                select(func.count()).where(Batch.provisional.is_(True))
            )
        ).scalar()
        or 0
    )

    # Reasons histogram across all provisional batches.
    reason_rows = (
        await session.execute(
            select(Batch.provisional_reasons).where(Batch.provisional.is_(True))
        )
    ).scalars().all()
    histogram: dict[str, int] = {}
    for raw in reason_rows:
        try:
            for code in json.loads(raw) if raw else []:
                histogram[code] = histogram.get(code, 0) + 1
        except (ValueError, TypeError):
            continue

    return {
        "by_status": {s: int(c) for s, c in status_rows},
        "provisional": provisional_count,
        "reasons_histogram": histogram,
    }


@router.get("/media/{operation_id}")
async def get_media(
    operation_id: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    from server import UPLOAD_DIR, _SAFE  # shared identity guard + storage root

    if not _SAFE.match(operation_id or ""):
        raise HTTPException(status_code=400, detail="invalid_operation_id")
    row = (
        await session.execute(
            select(MediaFile).where(MediaFile.operation_id == operation_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_media")

    path = Path(row.file_path)
    if not path.resolve().is_relative_to(Path(UPLOAD_DIR).resolve()):
        raise HTTPException(status_code=400, detail="path_traversal")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="media_missing")
    return FileResponse(
        str(path),
        media_type="application/octet-stream",
        filename=row.filename or f"{operation_id}.bin",
    )


# ---------------------------------------------------------------------------
# P2.4 — Lab flow. A lab tech (or admin) submits results for a batch; the SAME
# recompute the legacy X-Admin-Secret channel runs fires, so the assumed_*
# provisional reasons flip identically. The certificate PDF is stored via the
# media mechanism under a labcert-<uuid> operation id.
# ---------------------------------------------------------------------------


async def _load_batch(session: AsyncSession, batch_uuid: str) -> Batch:
    try:
        buid = _uuid.UUID(batch_uuid)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="invalid_batch_uuid")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == buid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="unknown_batch")
    return batch


@router.post("/batches/{batch_uuid}/lab-results")
async def submit_lab_results(
    batch_uuid: str,
    payload: LabResultsInput,
    _user: PortalUser = Depends(require_role("lab", "admin")),
    session: AsyncSession = Depends(get_session),
):
    from server import apply_lab_results  # the ONE lab-ingestion path (P2.4)

    batch = await _load_batch(session, batch_uuid)
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
    reasons = batch.provisional_reasons
    try:
        parsed = json.loads(reasons) if reasons else []
    except (ValueError, TypeError):
        parsed = []
    return {
        "status": "ok",
        "batch_uuid": batch_uuid,
        "provisional": batch.provisional,
        "reasons": parsed,
    }


@router.post("/batches/{batch_uuid}/lab-certificate", status_code=status.HTTP_201_CREATED)
async def upload_lab_certificate(
    batch_uuid: str,
    file: UploadFile = File(...),
    _user: PortalUser = Depends(require_role("lab", "admin")),
    session: AsyncSession = Depends(get_session),
):
    from server import UPLOAD_DIR

    batch = await _load_batch(session, batch_uuid)
    op = f"labcert-{batch.batch_uuid}"
    target_dir = Path(UPLOAD_DIR) / "labcerts"
    target_dir.mkdir(parents=True, exist_ok=True)
    fpath = target_dir / f"{op}.bin"
    data = await file.read()
    fpath.write_bytes(data)
    sha = hashlib.sha256(data).hexdigest()

    row = MediaFile(
        operation_id=op,
        file_path=str(fpath),
        sha256_hash=sha,
        filename=file.filename,
        batch_uuid=batch.batch_uuid,
    )
    session.add(row)
    try:
        await session.commit()
    except IntegrityError:
        # A re-submitted certificate overwrites the prior one (same op id).
        await session.rollback()
        existing = (
            await session.execute(
                select(MediaFile).where(MediaFile.operation_id == op)
            )
        ).scalar_one()
        existing.file_path = str(fpath)
        existing.sha256_hash = sha
        existing.filename = file.filename
        existing.batch_uuid = batch.batch_uuid
        await session.commit()
    return {"operation_id": op, "sha256_hash": sha}
