"""Phase 5 — Ed25519 test signing helpers.

A single fixed test keypair stands in for the device's on-device Ed25519
identity. Test devices enroll ``TEST_PUBLIC_KEY_B64``; requests are signed with
the matching private key. ``sign_request`` keeps its legacy positional
signature (the ``b64_key`` arg is now ignored) so existing call sites only need
to (a) enroll the public key and (b) send the ``X-Signature`` header.
"""
import base64
import hashlib
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# Deterministic 32-byte seed so the keypair (and every signature) is stable
# across runs and identical to the one conftest derives.
_SEED = bytes(range(32))
_PRIV = Ed25519PrivateKey.from_private_bytes(_SEED)


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("utf-8").rstrip("=")


def _public_key_b64() -> str:
    raw = _PRIV.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _b64u(raw)


# The base64url Ed25519 public key every test device enrolls with.
TEST_PUBLIC_KEY_B64 = _public_key_b64()


def sign_request(
    device_id: str,
    b64_key: str,
    method: str,
    path: str,
    op_id: str,
    payload: dict,
) -> str:
    """Ed25519-sign the canonical request string.

    ``b64_key`` is ignored (legacy HMAC parameter retained for call-site
    compatibility); signing always uses the fixed test private key whose public
    key is ``TEST_PUBLIC_KEY_B64``.
    """
    raw_body = json.dumps(payload).encode("utf-8")
    canonical = "\n".join(
        [method, path, op_id, hashlib.sha256(raw_body).hexdigest(), device_id]
    ).encode("utf-8")
    return _b64u(_PRIV.sign(canonical))


def sign_canonical(canonical: bytes) -> str:
    """Ed25519-sign an already-assembled canonical byte string with the fixed
    test private key. For call sites that build the canonical string inline."""
    return _b64u(_PRIV.sign(canonical))
