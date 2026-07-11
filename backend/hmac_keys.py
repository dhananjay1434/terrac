"""P3.6 — versioned HMAC keys for the server's own lca_signature.

Rotating the lca_signature key must NOT invalidate already-issued signatures.
Each batch records the key id it was signed under (``batches.lca_signature_key_id``)
and verification resolves that id, so an old batch keeps verifying under its
original key while new batches sign under the active key.

Scope: this is ONLY the server-side HMAC over the LCA audit. The device auth
path (Ed25519 signatures) is untouched.

Config (production):
    DMRV_HMAC_KEYS       = '{"k2":"<hex>","k1":"<hex>"}'   # id -> secret
    DMRV_HMAC_ACTIVE_KEY = 'k2'

Back-compat: if only the legacy ``DMRV_HMAC_SECRET`` is set, it is exposed as
key id ``k0`` and is active — a zero-config-change deploy keeps working, and
rows written before this change (null key id) resolve to ``k0``.

Env is read live (not captured at import) so a rotation can take effect without
a code change and so tests can monkeypatch it.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Dict, Optional, Tuple

# Default key id for the legacy single-secret and for historical null rows.
LEGACY_KEY_ID = "k0"

# Entropy floor (mirrors server._require_secret). Bypassed by DMRV_ALLOW_WEAK_SECRETS.
_MIN_SECRET_LEN = 32
_MIN_SECRET_UNIQUE = 10


def _weak_ok() -> bool:
    return os.environ.get("DMRV_ALLOW_WEAK_SECRETS") == "1"


def _check_entropy(key_id: str, secret: str) -> None:
    if _weak_ok():
        return
    if len(secret) < _MIN_SECRET_LEN or len(set(secret)) < _MIN_SECRET_UNIQUE:
        raise RuntimeError(
            f"HMAC key '{key_id}' is too weak: require >= {_MIN_SECRET_LEN} chars "
            f"and >= {_MIN_SECRET_UNIQUE} distinct characters."
        )


def load_keys() -> Dict[str, str]:
    """Resolve the id->secret map from the environment, or refuse to start."""
    raw = os.environ.get("DMRV_HMAC_KEYS")
    if raw:
        try:
            keys = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise RuntimeError("DMRV_HMAC_KEYS is not valid JSON.") from exc
        if not isinstance(keys, dict) or not keys:
            raise RuntimeError("DMRV_HMAC_KEYS must be a non-empty JSON object.")
        for kid, secret in keys.items():
            if not isinstance(kid, str) or not isinstance(secret, str) or not secret:
                raise RuntimeError("DMRV_HMAC_KEYS entries must be non-empty strings.")
            _check_entropy(kid, secret)
        return keys
    legacy = os.environ.get("DMRV_HMAC_SECRET")
    if not legacy:
        raise RuntimeError(
            "No HMAC key configured: set DMRV_HMAC_KEYS (+DMRV_HMAC_ACTIVE_KEY) "
            "or the legacy DMRV_HMAC_SECRET."
        )
    _check_entropy(LEGACY_KEY_ID, legacy)
    return {LEGACY_KEY_ID: legacy}


def active_key_id() -> str:
    """Id of the key new signatures use."""
    if os.environ.get("DMRV_HMAC_KEYS"):
        kid = os.environ.get("DMRV_HMAC_ACTIVE_KEY")
        keys = load_keys()
        if not kid or kid not in keys:
            raise RuntimeError(
                "DMRV_HMAC_ACTIVE_KEY must name a key present in DMRV_HMAC_KEYS."
            )
        return kid
    return LEGACY_KEY_ID


def active_key() -> Tuple[str, str]:
    """(key_id, secret) of the active signing key."""
    kid = active_key_id()
    return kid, load_keys()[kid]


def key_for(key_id: Optional[str]) -> Optional[str]:
    """Resolve a secret by id. A null id maps to the legacy k0 (historical rows).
    Returns None when the id isn't in the current env (rotated out) so callers
    can report 'unverifiable' instead of crashing."""
    resolved = key_id or LEGACY_KEY_ID
    return load_keys().get(resolved)


def sign(payload: bytes) -> Tuple[str, str]:
    """Sign under the active key. Returns (key_id, hex signature)."""
    kid, secret = active_key()
    sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return kid, sig


def verify(payload: bytes, signature: str, key_id: Optional[str]) -> str:
    """Verify a signature made under ``key_id``.

    Returns 'valid', 'invalid', or 'unverifiable' (the key id is not in the
    current environment — rotated out entirely). Never raises on a missing key.
    """
    secret = key_for(key_id)
    if secret is None:
        return "unverifiable"
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return "valid" if hmac.compare_digest(expected, signature) else "invalid"


def validate_startup() -> None:
    """Fail-loud at import if HMAC key config is missing/invalid — preserves the
    guarantee the old ``_require_secret('DMRV_HMAC_SECRET')`` gave."""
    active_key()  # raises on any misconfiguration
