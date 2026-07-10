"""Portal API router.

Mounted once from `server.py` via `app.include_router(router)`. Every new portal
endpoint hangs off THIS router — `server.py` only ever gains the single mount
line. Rate limiting for `/api/v1/portal/*` maps to the "admin" bucket in
`server._rl_bucket`.
"""

import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import EnrollmentToken, PortalUser
from .auth import (
    create_session,
    require_role,
    revoke_session,
    verify_login,
)
from .schemas import (
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
