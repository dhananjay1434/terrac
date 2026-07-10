"""Portal authentication: argon2 passwords, opaque hashed sessions, roles.

Devices sign with Ed25519; humans authenticate here. Passwords are argon2id
hashed; sessions are random 256-bit bearer tokens stored only as their SHA-256,
valid for 24h. `require_role(*roles)` is the FastAPI dependency that guards
portal endpoints. This module imports only `db` + `models` (no `server`), so it
carries no app/engine side effects.
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import PortalSession, PortalUser

VALID_ROLES = ("admin", "lab", "verifier")
SESSION_TTL = timedelta(hours=24)
_SESSION_TOKEN_BYTES = 32  # 256-bit opaque session token

_ph = PasswordHasher()
# A fixed argon2 hash used to keep login timing ~constant when the email is
# unknown (mitigates user enumeration by timing). Value is irrelevant.
_DUMMY_HASH = _ph.hash("dmrv-portal-dummy-password")


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def verify_login(stored_hash: Optional[str], password: str) -> bool:
    """Constant-ish-time login check. When [stored_hash] is None (unknown or
    disabled user) an argon2 verify still runs against a dummy hash so response
    timing doesn't reveal which emails exist; the result is always failure."""
    target = stored_hash or _DUMMY_HASH
    ok = verify_password(target, password)
    return ok if stored_hash else False


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime) -> datetime:
    # SQLite round-trips naive datetimes; treat a naive value as UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


async def create_session(session: AsyncSession, user_id: int) -> tuple[str, datetime]:
    """Mint a new opaque session token, persist only its hash, return the raw
    token (shown once) + its expiry."""
    raw = secrets.token_urlsafe(_SESSION_TOKEN_BYTES)
    expires = datetime.now(timezone.utc) + SESSION_TTL
    session.add(
        PortalSession(
            token_hash=_hash_token(raw),
            user_id=user_id,
            expires_at=expires,
        )
    )
    await session.commit()
    return raw, expires


async def revoke_session(session: AsyncSession, raw_token: str) -> None:
    row = (
        await session.execute(
            select(PortalSession).where(
                PortalSession.token_hash == _hash_token(raw_token)
            )
        )
    ).scalar_one_or_none()
    if row is not None:
        await session.delete(row)
        await session.commit()


def _bearer(authorization: Optional[str]) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer_token"
        )
    return authorization[7:].strip()


async def authenticate(
    authorization: Optional[str], session: AsyncSession
) -> PortalUser:
    """Resolve the current portal user from a `Bearer <token>` header, or raise
    401. Rejects unknown/expired sessions and disabled users."""
    token = _bearer(authorization)
    sess = (
        await session.execute(
            select(PortalSession).where(
                PortalSession.token_hash == _hash_token(token)
            )
        )
    ).scalar_one_or_none()
    if sess is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session"
        )
    if _as_utc(sess.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="session_expired"
        )
    user = (
        await session.execute(
            select(PortalUser).where(PortalUser.id == sess.user_id)
        )
    ).scalar_one_or_none()
    if user is None or user.disabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user_disabled"
        )
    return user


def require_role(*roles: str):
    """FastAPI dependency: authenticate the bearer session and enforce the
    caller's role. `require_role()` with no roles = any authenticated user."""

    async def _dep(
        authorization: Optional[str] = Header(None, alias="Authorization"),
        session: AsyncSession = Depends(get_session),
    ) -> PortalUser:
        user = await authenticate(authorization, session)
        if roles and user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="forbidden"
            )
        return user

    return _dep
