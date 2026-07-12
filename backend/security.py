"""Device Ed25519 signature verification + admin auth (extracted from server.py, R3).

Auth dependencies injected via FastAPI's Depends(). The device-signature functions
resolve the caller's device_id from the X-Device-Id / X-Signature headers and the
DeviceKey table; the admin guard compares X-Admin-Secret via constant-time compare.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.exceptions import InvalidSignature

import observability
from db import get_session
from models import DeviceKey
from settings import (
    _ADMIN_SECRET,
    _canonical_skew_seconds,
    _require_canonical_v2,
    log,
)


# Identifier guard reused for device_id / operation_id path segments (blocks
# path traversal + injection). Module-level so both the device media upload and
# the portal media download validate against the SAME pattern (P2.2).
_SAFE = re.compile(r"^[A-Za-z0-9_\-]{1,128}$")


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


async def verify_signature(
    request: Request,
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_canonical_version: Optional[str] = Header(None, alias="X-Canonical-Version"),
    x_signed_at: Optional[str] = Header(None, alias="X-Signed-At"),
    session: AsyncSession = Depends(get_session),
) -> str:
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature"
        )
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    device = (
        await session.execute(
            select(DeviceKey).where(DeviceKey.device_id == x_device_id)
        )
    ).scalar_one_or_none()
    if not device:
        log.error(f"Signature Error: unknown_device '{x_device_id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
    body_hash = hashlib.sha256(await request.body()).hexdigest()
    fields = [
        request.method.upper(),
        request.url.path,
        x_idempotency_key or "",
        body_hash,
        x_device_id,
    ]
    # T2.3: v2 binds a client timestamp and rejects stale/skewed requests (replay
    # window). v1 (no version header) is still accepted unless v2 is required.
    if x_canonical_version == "2":
        if not x_signed_at:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signed_at"
            )
        try:
            signed_at = int(x_signed_at)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="bad_signed_at"
            )
        if abs(int(time.time()) - signed_at) > _canonical_skew_seconds():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="stale_signature"
            )
        fields.append(str(signed_at))
    elif _require_canonical_v2():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="canonical_v2_required"
        )
    canonical = "\n".join(fields).encode("utf-8")
    try:
        pub.verify(_b64url_decode(x_signature), canonical)
    except InvalidSignature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="signature_mismatch"
        )
    # P4.2: count verified v1 (unversioned) traffic so the fleet's migration to
    # the v2 canonical is observable. DMRV_REQUIRE_CANONICAL_V2 is flipped on only
    # after this counter stays zero across the fleet for 14 days.
    if x_canonical_version != "2":
        observability.record_canonical_v1(request.url.path)
    return x_device_id


async def verify_media_signature(
    x_device_id: Optional[str] = Header(None, alias="X-Device-Id"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_declared_sha256: Optional[str] = Header(None, alias="X-Declared-SHA256"),
    x_batch_uuid: Optional[str] = Header(None, alias="X-Batch-UUID"),
    session: AsyncSession = Depends(get_session),
) -> str:
    """Phase 15-A: Ed25519 auth for the media evidence channel.

    FROZEN media canonical — MUST byte-match the client's CryptoSigner.signMediaUpload:
        POST\\n/api/v1/media\\n{idempotency_key}\\n{declared_sha256_lower}\\n{batch_uuid}\\n{device_id}
    We sign the DECLARED file hash rather than sha256(multipart body) — the client
    cannot reproduce the exact multipart bytes. upload_media separately enforces
    calculated_hash == declared, so signing the declared hash binds the real bytes.
    """
    if not x_signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_signature"
        )
    if not x_device_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    device = (
        await session.execute(
            select(DeviceKey).where(DeviceKey.device_id == x_device_id)
        )
    ).scalar_one_or_none()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="unknown_device"
        )
    pub = Ed25519PublicKey.from_public_bytes(_b64url_decode(device.public_key))
    canonical = "\n".join(
        [
            "POST",
            "/api/v1/media",
            x_idempotency_key or "",
            (x_declared_sha256 or "").lower(),
            x_batch_uuid or "",
            x_device_id,
        ]
    ).encode("utf-8")
    try:
        pub.verify(_b64url_decode(x_signature), canonical)
    except InvalidSignature:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="signature_mismatch"
        )
    return x_device_id


def _require_admin(x_admin_secret: str) -> None:
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized"
        )
