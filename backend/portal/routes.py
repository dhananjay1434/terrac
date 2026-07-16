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
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import (
    AuditEvent,
    Batch,
    CompositePileSample,
    DeviceKey,
    EndUseApplication,
    Kiln,
    MediaFile,
    MoistureReading,
    PortalUser,
    PyrolysisTelemetry,
    TransportEvent,
    YieldMetrics,
    EnrollmentToken,
)
# P2.5: reuse the admin registry request models + upsert helpers directly from
# schemas + services.registry (P4.8/R7 — repointed off server to break the cycle).
from schemas import (
    AnnualVerificationRequest,
    KilnRequest,
    OperatorTrainingRequest,
    ScaleCalibrationRequest,
    SupervisorVisitRequest,
)
from services.registry import (
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
from routers.devices import _hash_enroll_token
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


async def write_audit(
    session: AsyncSession,
    *,
    event_type: str,
    actor_user_id: Optional[int],
    batch_uuid: Optional[str] = None,
    payload: Optional[dict] = None,
) -> None:
    """Append one row to the immutable audit trail (P2.6). The caller commits."""
    session.add(
        AuditEvent(
            event_type=event_type,
            batch_uuid=batch_uuid,
            actor_user_id=actor_user_id,
            payload_json=json.dumps(payload or {}),
        )
    )

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
    admin: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Admin-only: mint a single-use device enrollment token (256-bit) and
    return it plus a scannable QR payload `dmrv-enroll:v1:{...}`."""
    token = secrets.token_urlsafe(_ENROLL_TOKEN_BYTES)
    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    # Audit fix 6: store only the SHA-256 hash; the raw token is returned once
    # below (QR + response) and never persisted.
    session.add(EnrollmentToken(token=_hash_enroll_token(token), expires_at=expires))
    await write_audit(
        session,
        event_type="token_minted",
        actor_user_id=admin.id,
        payload={"expires_at": expires.isoformat()},
    )
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

    from services.compliance import compliance_view  # reuse the ONE grading view (P2.0 coupling)

    try:
        buid = str(_uuid.UUID(batch_uuid))
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
    from security import _SAFE  # shared identity guard
    from storage import get_storage

    if not _SAFE.match(operation_id or ""):
        raise HTTPException(status_code=400, detail="invalid_operation_id")
    row = (
        await session.execute(
            select(MediaFile).where(MediaFile.operation_id == operation_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="unknown_media")

    # P3.2: read back through the storage abstraction (local FS or S3/MinIO).
    # file_path holds an abstract key for new rows and a legacy absolute path
    # for old ones; the local backend resolves both and guards traversal.
    storage = get_storage()
    try:
        stream = storage.open_stream(row.file_path)
    except ValueError:
        raise HTTPException(status_code=400, detail="path_traversal")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="media_missing")
    filename = row.filename or f"{operation_id}.bin"
    return StreamingResponse(
        stream,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# P2.4 — Lab flow. A lab tech (or admin) submits results for a batch; the SAME
# recompute the legacy X-Admin-Secret channel runs fires, so the assumed_*
# provisional reasons flip identically. The certificate PDF is stored via the
# media mechanism under a labcert-<uuid> operation id.
# ---------------------------------------------------------------------------


async def _load_batch(session: AsyncSession, batch_uuid: str) -> Batch:
    try:
        buid = str(_uuid.UUID(batch_uuid))
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
    user: PortalUser = Depends(require_role("lab", "admin")),
    session: AsyncSession = Depends(get_session),
):
    from services.lab import apply_lab_results  # the ONE lab-ingestion path (P2.4)

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
    await write_audit(
        session,
        event_type="lab_results",
        actor_user_id=user.id,
        batch_uuid=batch_uuid,
        payload={"provisional": batch.provisional},
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
    from storage import get_storage

    batch = await _load_batch(session, batch_uuid)
    op = f"labcert-{batch.batch_uuid}"
    data = await file.read()
    sha = hashlib.sha256(data).hexdigest()
    # P3.2: store the certificate under the "labcerts" prefix via the abstraction.
    stored_key = get_storage().write(op, "labcerts", data)

    row = MediaFile(
        operation_id=op,
        file_path=stored_key,
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
        existing.file_path = stored_key
        existing.sha256_hash = sha
        existing.filename = file.filename
        existing.batch_uuid = batch.batch_uuid
        await session.commit()
    return {"operation_id": op, "sha256_hash": sha}


# ---------------------------------------------------------------------------
# P2.5 — Registry admin forms. Thin portal (admin-role) wrappers over the SAME
# upsert helpers the legacy X-Admin-Secret routes use. Operator-training and
# supervisor-visit are idempotent on their natural key (M5).
# ---------------------------------------------------------------------------


@router.post("/registry/kilns")
async def portal_register_kiln(
    payload: KilnRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_kiln(session, payload)
    await write_audit(
        session,
        event_type="kiln_registered",
        actor_user_id=user.id,
        payload={"kiln_id": payload.kiln_id},
    )
    await session.commit()
    return result


@router.get("/registry/kilns")
async def portal_list_kilns(
    _user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(select(Kiln).order_by(Kiln.registered_at.desc()))
    ).scalars().all()
    return {
        "kilns": [
            {
                "kiln_id": k.kiln_id,
                "kiln_type": k.kiln_type,
                "material": k.material,
                "weight_kg": k.weight_kg,
                "lifetime_years": k.lifetime_years,
            }
            for k in rows
        ]
    }


@router.post("/registry/operator-training")
async def portal_operator_training(
    payload: OperatorTrainingRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_operator_training(session, payload)
    await write_audit(
        session,
        event_type="operator_training",
        actor_user_id=user.id,
        payload={"operator_id": payload.operator_id},
    )
    await session.commit()
    return result


@router.post("/registry/supervisor-visit")
async def portal_supervisor_visit(
    payload: SupervisorVisitRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_supervisor_visit(session, payload)
    await write_audit(
        session,
        event_type="supervisor_visit",
        actor_user_id=user.id,
        payload={"kiln_id": payload.kiln_id},
    )
    await session.commit()
    return result


@router.post("/registry/scale-calibration")
async def portal_scale_calibration(
    payload: ScaleCalibrationRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_scale_calibration(session, payload)
    await write_audit(
        session,
        event_type="scale_calibration",
        actor_user_id=user.id,
        payload={"scale_id": payload.scale_id},
    )
    await session.commit()
    return result


@router.post("/registry/annual-verification")
async def portal_annual_verification(
    payload: AnnualVerificationRequest,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    result = await upsert_annual_verification(session, payload)
    await write_audit(
        session,
        event_type="annual_verification",
        actor_user_id=user.id,
        payload={"project_id": payload.project_id, "year": payload.year},
    )
    await session.commit()
    return result


# ---------------------------------------------------------------------------
# P2.6 — Deliberate credit issuance. Admin-only, re-verified server-side, and
# recorded in the append-only audit trail.
# ---------------------------------------------------------------------------


@router.post("/batches/{batch_uuid}/issue")
async def issue_credit(
    batch_uuid: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    batch = await _load_batch(session, batch_uuid)
    if batch.status == "ISSUED":
        raise HTTPException(status_code=409, detail="already_issued")
    # Never trust the UI: the server's own provisional flag (recomputed from all
    # gates) is the authority — a provisional batch can never be issued.
    if batch.provisional:
        raise HTTPException(status_code=409, detail="batch_provisional")

    batch.status = "ISSUED"
    await write_audit(
        session,
        event_type="credit_issued",
        actor_user_id=user.id,
        batch_uuid=str(batch.batch_uuid),
        payload={
            "net_credit_t_co2e": batch.net_credit_t_co2e,
            "lca_signature": batch.lca_signature,
        },
    )
    await session.commit()
    return {
        "status": "ISSUED",
        "batch_uuid": batch_uuid,
        "net_credit_t_co2e": batch.net_credit_t_co2e,
    }


@router.get("/batches/{batch_uuid}/export/{fmt}")
async def export_batch(
    batch_uuid: str,
    fmt: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """Portal-native registry export (Bearer + admin role).

    Reuses the SAME CSIExportService/RainbowExportService as the admin-secret
    ops endpoints (routers/exports.py), so the browser never needs the admin
    secret. Provisional batches are rejected — a batch that cannot be issued
    cannot be exported.
    """
    from services.export import CSIExportService, RainbowExportService

    if fmt not in ("csi", "rainbow"):
        raise HTTPException(status_code=400, detail="unknown_export_format")

    batch = await _load_batch(session, batch_uuid)
    if batch.provisional:
        reasons = batch.provisional_reasons
        try:
            parsed = json.loads(reasons) if reasons else []
        except (ValueError, TypeError):
            parsed = []
        raise HTTPException(
            status_code=409,
            detail={"error": "batch_provisional", "reasons": parsed},
        )

    try:
        if fmt == "csi":
            report = await CSIExportService.export_batch_as_csi(batch, session)
        else:
            report = await RainbowExportService.export_batch_as_rainbow(batch, session)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    await write_audit(
        session,
        event_type="batch_exported",
        actor_user_id=user.id,
        batch_uuid=str(batch.batch_uuid),
        payload={"format": fmt},
    )
    await session.commit()
    return report


@router.get("/batches/{batch_uuid}/audit")
async def batch_audit(
    batch_uuid: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    rows = (
        await session.execute(
            select(AuditEvent)
            .where(AuditEvent.batch_uuid == batch_uuid)
            .order_by(AuditEvent.created_at.asc())
        )
    ).scalars().all()
    return {
        "events": [
            {
                "event_type": e.event_type,
                "actor_user_id": e.actor_user_id,
                "payload": json.loads(e.payload_json or "{}"),
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in rows
        ]
    }
