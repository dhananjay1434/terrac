"""PR-1 — credit issuance ledger: portal endpoints.

Kept as its own router (not folded into the already-large portal/routes.py)
so the issuance lifecycle stays a single, thin, reviewable module. Mounted
separately in app_factory.py under the same "/api/v1/portal" prefix.

All status-machine + precondition rules live in services/issuance_state.py
(pure, no DB/HTTP) — this router is the thin DB edge that calls them and
persists the result, mirroring routers/dispatch.py's shape.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import Batch, CreditIssuance, PortalUser
from services import issuance_state as iss

from .auth import require_role
from .routes import write_audit
from .schemas import IssuanceListResponse, IssuanceOut, IssuanceRetireInput

router = APIRouter(prefix="/api/v1/portal", tags=["portal-issuance"])

_PAGE_MAX = 100


def _issuance_row(row: CreditIssuance) -> dict:
    return {
        "issuance_uuid": row.issuance_uuid,
        "batch_uuid": row.batch_uuid,
        "serial": row.serial,
        "vintage": row.vintage,
        "t_co2e_frozen": row.t_co2e_frozen,
        "methodology_version": row.methodology_version,
        "status": row.status,
        "verified_by_user_id": row.verified_by_user_id,
        "issued_at": row.issued_at.isoformat() if row.issued_at else None,
        "registry_submission_ref": row.registry_submission_ref,
        "created_at": row.created_at.isoformat(),
    }


async def _get_batch_or_404(session: AsyncSession, batch_uuid: str) -> Batch:
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == batch_uuid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=404, detail="batch_not_found")
    return batch


async def _get_issuance(
    session: AsyncSession, batch_uuid: str
) -> Optional[CreditIssuance]:
    return (
        await session.execute(
            select(CreditIssuance).where(CreditIssuance.batch_uuid == batch_uuid)
        )
    ).scalar_one_or_none()


@router.post(
    "/batches/{batch_uuid}/issuance/verify",
    response_model=IssuanceOut,
)
async def verify_issuance(
    batch_uuid: str,
    user: PortalUser = Depends(require_role("verifier", "admin")),
    session: AsyncSession = Depends(get_session),
):
    """Records independent verification (PR-2 hardens the gate itself; here
    the `require_role` dependency already enforces a distinct verifier/admin
    human channel — a portal user, never the producing device)."""
    await _get_batch_or_404(session, batch_uuid)

    issuance = await _get_issuance(session, batch_uuid)
    if issuance is None:
        issuance = CreditIssuance(
            issuance_uuid=str(_uuid.uuid4()),
            batch_uuid=batch_uuid,
            status="pending",
        )
        session.add(issuance)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            issuance = await _get_issuance(session, batch_uuid)

    try:
        iss.validate_transition(issuance.status, "verified")
    except iss.IllegalIssuanceTransition as exc:
        raise HTTPException(
            status_code=409, detail={"code": "illegal_transition", "message": str(exc)}
        )

    issuance.status = "verified"
    issuance.verified_by_user_id = user.id

    await write_audit(
        session,
        event_type="issuance_verified",
        actor_user_id=user.id,
        batch_uuid=batch_uuid,
    )
    await session.commit()
    await session.refresh(issuance)
    return _issuance_row(issuance)


@router.post(
    "/batches/{batch_uuid}/issuance/issue",
    response_model=IssuanceOut,
)
async def issue_issuance(
    batch_uuid: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    batch = await _get_batch_or_404(session, batch_uuid)
    issuance = await _get_issuance(session, batch_uuid)

    if issuance is None:
        # No verify step was ever recorded — reject with the same
        # illegal-transition semantics as an explicit pending->issued attempt.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "illegal_transition",
                "message": "no issuance record — batch has not been verified",
            },
        )

    if issuance.status == "issued":
        # Idempotent: re-issuing an already-issued batch returns the existing
        # issuance, never a second row / second serial.
        return _issuance_row(issuance)

    try:
        iss.validate_transition(issuance.status, "issued")
    except iss.IllegalIssuanceTransition as exc:
        raise HTTPException(
            status_code=409, detail={"code": "illegal_transition", "message": str(exc)}
        )

    try:
        iss.assert_issuable(
            batch_is_provisional=batch.provisional,
            batch_is_signed=bool(batch.lca_signature),
            independently_verified=True,
        )
    except iss.IssuanceNotReady as exc:
        raise HTTPException(
            status_code=422, detail={"code": "not_issuable", "message": str(exc)}
        )

    vintage = batch.harvest_timestamp.year
    project_component = batch.project_id or "unscoped"
    issued_count = (
        await session.execute(
            select(CreditIssuance).where(
                CreditIssuance.status == "issued",
                CreditIssuance.vintage == vintage,
            )
        )
    ).scalars().all()
    sequence = len(issued_count) + 1
    serial = iss.make_serial(project_component, vintage, sequence)

    issuance.status = "issued"
    issuance.serial = serial
    issuance.vintage = vintage
    issuance.t_co2e_frozen = batch.net_credit_t_co2e
    issuance.methodology_version = batch.lca_methodology_version
    issuance.issued_at = datetime.now(timezone.utc)
    # Keep the legacy Batch.status field (the pre-ledger `/batches/{uuid}/issue`
    # endpoint's source of truth) in sync so nothing reading batch.status still
    # sees "RECEIVED" once this ledger has actually issued the credit.
    batch.status = "ISSUED"

    try:
        await write_audit(
            session,
            event_type="issuance_issued",
            actor_user_id=user.id,
            batch_uuid=batch_uuid,
            payload={"serial": serial},
        )
        await session.commit()
    except IntegrityError:
        # Lost a race on the unique `serial` constraint (concurrent issuance
        # of a different batch computed the same sequence number) — the
        # batch-level `batch_uuid` uniqueness is unaffected; surface a 409 so
        # the caller retries rather than silently duplicating.
        await session.rollback()
        raise HTTPException(status_code=409, detail="issuance_serial_conflict")

    await session.refresh(issuance)
    return _issuance_row(issuance)


@router.post(
    "/batches/{batch_uuid}/issuance/retire",
    response_model=IssuanceOut,
)
async def retire_issuance(
    batch_uuid: str,
    payload: IssuanceRetireInput,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    issuance = await _get_issuance(session, batch_uuid)
    if issuance is None:
        raise HTTPException(status_code=404, detail="issuance_not_found")

    try:
        iss.validate_transition(issuance.status, "retired")
    except iss.IllegalIssuanceTransition as exc:
        raise HTTPException(
            status_code=409, detail={"code": "illegal_transition", "message": str(exc)}
        )

    issuance.status = "retired"
    if payload.registry_submission_ref is not None:
        issuance.registry_submission_ref = payload.registry_submission_ref

    await write_audit(
        session,
        event_type="issuance_retired",
        actor_user_id=user.id,
        batch_uuid=batch_uuid,
    )
    await session.commit()
    await session.refresh(issuance)
    return _issuance_row(issuance)


@router.post(
    "/batches/{batch_uuid}/issuance/cancel",
    response_model=IssuanceOut,
)
async def cancel_issuance(
    batch_uuid: str,
    user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    issuance = await _get_issuance(session, batch_uuid)
    if issuance is None:
        raise HTTPException(status_code=404, detail="issuance_not_found")

    try:
        iss.validate_transition(issuance.status, "cancelled")
    except iss.IllegalIssuanceTransition as exc:
        raise HTTPException(
            status_code=409, detail={"code": "illegal_transition", "message": str(exc)}
        )

    issuance.status = "cancelled"

    await write_audit(
        session,
        event_type="issuance_cancelled",
        actor_user_id=user.id,
        batch_uuid=batch_uuid,
    )
    await session.commit()
    await session.refresh(issuance)
    return _issuance_row(issuance)


@router.get("/issuances", response_model=IssuanceListResponse)
async def list_issuances(
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
    status_eq: Optional[str] = Query(None, alias="status"),
    project_id: Optional[str] = None,
    before: Optional[str] = Query(None, description="cursor: created_at ISO"),
    limit: int = Query(50, ge=1, le=_PAGE_MAX),
):
    stmt = select(CreditIssuance)
    if status_eq is not None:
        stmt = stmt.where(CreditIssuance.status == status_eq)
    if project_id is not None:
        stmt = stmt.join(Batch, Batch.batch_uuid == CreditIssuance.batch_uuid).where(
            Batch.project_id == project_id
        )
    if before:
        stmt = stmt.where(
            CreditIssuance.created_at < datetime.fromisoformat(before)
        )
    stmt = stmt.order_by(
        CreditIssuance.created_at.desc(), CreditIssuance.id.desc()
    ).limit(limit + 1)

    rows = list((await session.execute(stmt)).scalars().all())
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1].created_at.isoformat() if has_more and rows else None
    return {
        "issuances": [_issuance_row(r) for r in rows],
        "next_cursor": next_cursor,
    }
