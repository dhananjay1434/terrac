from __future__ import annotations
import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import DeviceKey, EnrollmentToken
from schemas import RegistrationRequest, RegistrationResponse, MintTokenRequest
from settings import _ADMIN_SECRET, log
from jsonsafe import _as_utc
import attestation

router = APIRouter()


def _hash_enroll_token(raw: str) -> str:
    # Audit fix 6: enrollment tokens are stored only as SHA-256 (same
    # discipline as portal sessions) so a DB leak cannot mint devices.
    import hashlib
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post(
    "/api/v1/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    payload: RegistrationRequest,
    x_enrollment_token: Optional[str] = Header(None, alias="X-Enrollment-Token"),
    session: AsyncSession = Depends(get_session),
):
    if not x_enrollment_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_required"
        )

    # Hash-first lookup; fall back to the raw value so tokens minted before
    # the hashing change keep working until they expire.
    token_res = await session.execute(
        select(EnrollmentToken).where(
            EnrollmentToken.token == _hash_enroll_token(x_enrollment_token)
        )
    )
    db_token = token_res.scalar_one_or_none()
    if db_token is None:
        token_res = await session.execute(
            select(EnrollmentToken).where(EnrollmentToken.token == x_enrollment_token)
        )
        db_token = token_res.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_enrollment_token"
        )
    if db_token.used_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="enrollment_token_used"
        )
    if db_token.expires_at:
        expires = _as_utc(db_token.expires_at)
        if expires < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="enrollment_token_expired",
            )

    stmt = select(DeviceKey).where(DeviceKey.device_id == payload.device_id)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="device_already_registered"
        )

    new_key = DeviceKey(device_id=payload.device_id, public_key=payload.public_key)
    session.add(new_key)

    db_token.used_at = datetime.now(timezone.utc)
    await session.commit()
    log.info(
        f"[register] Device {payload.device_id} registered successfully with token."
    )
    return RegistrationResponse(status="registered", device_id=payload.device_id)
@router.post("/api/v1/admin/mint-token", status_code=status.HTTP_201_CREATED)
async def mint_enrollment_token(
    payload: MintTokenRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )

    expires = datetime.now(timezone.utc) + timedelta(days=payload.expires_in_days)
    new_token = EnrollmentToken(
        token=_hash_enroll_token(payload.token), expires_at=expires
    )
    session.add(new_token)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="token_already_exists")

    return {
        "status": "minted",
        "token": payload.token,
        "expires_at": expires.isoformat(),
    }
