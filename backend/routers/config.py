"""V8 Part 0.4 — remote control plane: signed feature flags, kill-switch,
and minimum supported app version.

A private-APK + CI-off fleet otherwise has zero remote control: a bad build
or a discovered fraud vector can't be flag-gated or force-updated post-
deploy. No Firebase needed — a signed boot-time config document suffices,
reusing the server signing key from Part 0.1 (server signs, app verifies —
the same direction as the /pubkeys endpoint).

Dormant-safe: an empty (or never-written) `app_config` row serves inert
defaults (kill_switch=False, min_version=None, flags={}) — identical to
today's behavior with no remote config at all. Signing is likewise dormant:
if the server signing key isn't configured (Part 0.1), the response reports
`signing_configured: false` and the app must treat an unsigned config as
"no remote config available" (fail safe, never enforce on an unverified
document).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from models import AppConfig
import server_signing

router = APIRouter()

_DEFAULT_CONFIG_ID = "default"


def _canonical_payload(doc: dict) -> bytes:
    """Deterministic byte representation of the signed fields the app must
    reproduce byte-for-byte to verify the signature.

    Contract (mirrored by lib/services/remote_config_service.dart
    canonicalPayload): sort_keys=True (recursive — sorts the nested `flags`
    map too), compact separators (no whitespace), and ensure_ascii=False so
    non-ASCII strings (e.g. a Hindi kill-switch message) are emitted as raw
    UTF-8. ensure_ascii=True would \\uXXXX-escape them, which Dart's jsonEncode
    never does — the two sides would then disagree and every device would
    reject a perfectly valid config exactly when (kill-switch) it matters most.
    """
    return json.dumps(
        doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")


@router.get("/api/v1/config")
async def get_config(session: AsyncSession = Depends(get_session)) -> dict:
    row = (
        await session.execute(
            select(AppConfig).where(AppConfig.config_id == _DEFAULT_CONFIG_ID)
        )
    ).scalar_one_or_none()

    if row is None:
        flags: dict = {}
        min_version = None
        kill_switch = False
        message = None
        updated_at = None
    else:
        try:
            flags = json.loads(row.flags_json) if row.flags_json else {}
        except (ValueError, TypeError):
            flags = {}
        min_version = row.min_version
        kill_switch = row.kill_switch
        message = row.message
        updated_at = row.updated_at.isoformat() if row.updated_at else None

    # NOTE: this is a READ endpoint that merely REPORTS config — it decides
    # nothing and rejects nothing (the app enforces the kill-switch/min-version
    # client-side). Emitting gate-rejection metrics here was wrong: it fired on
    # every device boot-poll (min_version is set in normal steady state) and
    # would explode the counter during an actual kill-switch emergency when the
    # whole fleet hammers this endpoint, drowning real fraud signals. If a
    # "kill-switch is active" signal is wanted, expose it as a single gauge
    # elsewhere, not a per-request counter here.

    signed_fields = {
        "flags": flags,
        "min_version": min_version,
        "kill_switch": kill_switch,
        "message": message,
        "signed_at": updated_at,
    }

    try:
        kid, signature = server_signing.sign(_canonical_payload(signed_fields))
    except RuntimeError:
        return {**signed_fields, "signing_configured": False, "kid": None, "signature": None}

    return {**signed_fields, "signing_configured": True, "kid": kid, "signature": signature}
