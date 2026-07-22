"""V8 Part 0.1 — server-side Ed25519 signing + kid rotation.

Opposite direction from the device-auth path in security.py (device signs,
server verifies): here the SERVER signs and the APP verifies. Two future
consumers share this module: Part 1's signed field-walk link and Part 0.4's
signed remote-config document.

Rotation model mirrors hmac_keys.py's versioned-key pattern:
    DMRV_SERVER_SIGNING_SK       = '<base64url, unpadded, 32-byte Ed25519 seed>'
    DMRV_SERVER_SIGNING_KID      = 'sk1'   # id of the CURRENT signer
    DMRV_SERVER_SIGNING_PUBKEYS  = '{"sk1":"<base64url pubkey>","sk0":"<...>"}'
        # the full VERIFY set — every kid whose signatures must still verify,
        # including the current signer's own pubkey.

Rotation runbook (docs/SERVER_SIGNING_KEY.md): add the new key's pubkey to
DMRV_SERVER_SIGNING_PUBKEYS FIRST (so apps can verify it before it's used),
deploy, THEN flip DMRV_SERVER_SIGNING_SK/_KID to make it the signer. Never
remove an old kid from the verify set while any issued artifact signed under
it can still be presented (config docs are short-lived; field-walk links are
single-use — the safe overlap window is short and documented in the runbook).

Unlike hmac_keys.validate_startup(), this module does NOT fail at import —
signing is dormant until a feature (0.4's remote config, Part 1's field-walk
link) actually calls sign()/public_keys(). Misconfiguration surfaces as a
RuntimeError at first use, not at every process boot, so the flag stays truly
optional for deployments that never enable those features.
"""

from __future__ import annotations

import base64
import json
import os
from typing import Dict, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


def _b64u_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("utf-8").rstrip("=")


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _load_private_key() -> Ed25519PrivateKey:
    raw = os.environ.get("DMRV_SERVER_SIGNING_SK")
    if not raw:
        raise RuntimeError(
            "DMRV_SERVER_SIGNING_SK is not set — server signing is not configured."
        )
    try:
        seed = _b64u_decode(raw)
    except Exception as exc:  # noqa: BLE001 - surface as a config error, not a crash
        raise RuntimeError("DMRV_SERVER_SIGNING_SK is not valid base64url.") from exc
    if len(seed) != 32:
        raise RuntimeError(
            "DMRV_SERVER_SIGNING_SK must decode to exactly 32 bytes "
            f"(got {len(seed)})."
        )
    return Ed25519PrivateKey.from_private_bytes(seed)


def current_kid() -> str:
    """Id of the key that new signatures are issued under."""
    kid = os.environ.get("DMRV_SERVER_SIGNING_KID")
    if not kid:
        raise RuntimeError(
            "DMRV_SERVER_SIGNING_KID is not set — server signing is not configured."
        )
    return kid


def public_keys() -> Dict[str, str]:
    """The full verify set: kid -> base64url raw public key.

    Must include the current signer's own kid (checked by validate_consistency,
    exercised in tests) so a freshly-signed artifact is always verifiable against
    this same map.
    """
    raw = os.environ.get("DMRV_SERVER_SIGNING_PUBKEYS")
    if not raw:
        raise RuntimeError(
            "DMRV_SERVER_SIGNING_PUBKEYS is not set — server signing is not configured."
        )
    try:
        keys = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise RuntimeError("DMRV_SERVER_SIGNING_PUBKEYS is not valid JSON.") from exc
    if not isinstance(keys, dict) or not keys:
        raise RuntimeError(
            "DMRV_SERVER_SIGNING_PUBKEYS must be a non-empty JSON object."
        )
    for kid, pub in keys.items():
        if not isinstance(kid, str) or not isinstance(pub, str) or not pub:
            raise RuntimeError(
                "DMRV_SERVER_SIGNING_PUBKEYS entries must be non-empty strings."
            )
    return keys


def validate_consistency() -> None:
    """Raise if the current signer's derived pubkey isn't in the verify set
    under its own kid — a misconfigured deploy would otherwise sign artifacts
    nothing can verify. Call this from ops tooling / a startup check for any
    process that actually signs (not a blanket import-time guard, per module
    docstring: signing stays optional until a feature enables it)."""
    kid = current_kid()
    keys = public_keys()
    if kid not in keys:
        raise RuntimeError(
            f"DMRV_SERVER_SIGNING_KID='{kid}' has no entry in "
            "DMRV_SERVER_SIGNING_PUBKEYS — add it before this key can sign."
        )
    priv = _load_private_key()
    derived = _b64u_encode(
        priv.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
    )
    if derived != keys[kid]:
        raise RuntimeError(
            f"DMRV_SERVER_SIGNING_SK does not match the declared pubkey for kid "
            f"'{kid}' in DMRV_SERVER_SIGNING_PUBKEYS — check for a copy/paste or "
            "rotation-order mistake."
        )


def sign(payload: bytes) -> Tuple[str, str]:
    """Sign under the current key. Returns (kid, base64url signature)."""
    kid = current_kid()
    priv = _load_private_key()
    sig = priv.sign(payload)
    return kid, _b64u_encode(sig)


def verify(payload: bytes, signature_b64: str, kid: str) -> str:
    """Verify a signature claimed to be made under `kid`.

    Returns 'valid', 'invalid', or 'unverifiable' (kid not in the current
    verify set — rotated out or never known). Never raises.
    """
    try:
        keys = public_keys()
    except RuntimeError:
        return "unverifiable"
    pub_b64 = keys.get(kid)
    if pub_b64 is None:
        return "unverifiable"
    try:
        pub = Ed25519PublicKey.from_public_bytes(_b64u_decode(pub_b64))
        pub.verify(_b64u_decode(signature_b64), payload)
    except (InvalidSignature, ValueError):
        return "invalid"
    return "valid"
