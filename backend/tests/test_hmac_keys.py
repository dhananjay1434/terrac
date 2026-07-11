"""P3.6 — versioned HMAC keys for lca_signature.

Rotation-safety: a batch signed under k1 still verifies after the active key
moves to k2; a key id that has been rotated out of the environment reports
'unverifiable' rather than crashing. Legacy single-secret deploys keep working
as key id k0.
"""

import json
from types import SimpleNamespace

import pytest

import hmac_keys
from lca_engine import sign_lca_audit


# --------------------------------------------------------------------------
# Key resolution
# --------------------------------------------------------------------------
def test_legacy_secret_is_exposed_as_k0(monkeypatch):
    monkeypatch.delenv("DMRV_HMAC_KEYS", raising=False)
    monkeypatch.setenv("DMRV_HMAC_SECRET", "legacy-secret-value")
    assert hmac_keys.active_key_id() == "k0"
    assert hmac_keys.load_keys() == {"k0": "legacy-secret-value"}


def test_versioned_keys_select_active(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k2": "sec2", "k1": "sec1"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k2")
    kid, secret = hmac_keys.active_key()
    assert kid == "k2"
    assert secret == "sec2"


def test_active_key_must_exist_in_map(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "sec1"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k9")
    with pytest.raises(RuntimeError):
        hmac_keys.active_key_id()


def test_no_key_configured_raises(monkeypatch):
    monkeypatch.delenv("DMRV_HMAC_KEYS", raising=False)
    monkeypatch.delenv("DMRV_HMAC_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        hmac_keys.load_keys()


# --------------------------------------------------------------------------
# Sign / verify + rotation
# --------------------------------------------------------------------------
def test_sign_under_k1_then_rotate_to_k2_old_still_verifies(monkeypatch):
    payload = b"the-signed-lca-payload"

    # Active key is k1; sign.
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "secret-one"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k1")
    kid1, sig1 = hmac_keys.sign(payload)
    assert kid1 == "k1"

    # Rotate: k2 becomes active, k1 is retained for verification.
    monkeypatch.setenv(
        "DMRV_HMAC_KEYS", json.dumps({"k2": "secret-two", "k1": "secret-one"})
    )
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k2")

    # The old signature still verifies under its recorded key id.
    assert hmac_keys.verify(payload, sig1, "k1") == "valid"
    # A new signature now uses k2.
    kid2, _ = hmac_keys.sign(payload)
    assert kid2 == "k2"


def test_rotated_out_key_is_unverifiable_not_a_crash(monkeypatch):
    payload = b"p"
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "secret-one"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k1")
    _, sig = hmac_keys.sign(payload)

    # k1 is fully removed from the environment.
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k2": "secret-two"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k2")
    assert hmac_keys.verify(payload, sig, "k1") == "unverifiable"


def test_tampered_signature_is_invalid(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "secret-one"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k1")
    kid, sig = hmac_keys.sign(b"payload")
    assert hmac_keys.verify(b"payload", "0" * 64, kid) == "invalid"


def test_null_key_id_resolves_to_legacy_k0(monkeypatch):
    """Historical rows have a null key id — they must verify under k0."""
    monkeypatch.delenv("DMRV_HMAC_KEYS", raising=False)
    monkeypatch.setenv("DMRV_HMAC_SECRET", "legacy-secret-value")
    _, sig = hmac_keys.sign(b"payload")  # signs under k0
    assert hmac_keys.verify(b"payload", sig, None) == "valid"


# --------------------------------------------------------------------------
# Batch-level verification through server.verify_lca_signature
# --------------------------------------------------------------------------
def test_batch_signature_verifies_after_rotation(monkeypatch):
    from server import verify_lca_signature

    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "secret-one"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k1")

    lca = SimpleNamespace(total=1.5, corg=0.8, method="x")
    buid = "11111111-1111-1111-1111-111111111111"
    key_id, secret = hmac_keys.active_key()
    sig = sign_lca_audit(lca, secret, batch_uuid=buid)
    batch = SimpleNamespace(
        batch_uuid=buid, lca_signature=sig, lca_signature_key_id=key_id
    )

    # Rotate active to k2, keep k1.
    monkeypatch.setenv(
        "DMRV_HMAC_KEYS", json.dumps({"k2": "secret-two", "k1": "secret-one"})
    )
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k2")
    assert verify_lca_signature(batch, lca) == "valid"


def test_batch_unsigned_and_unverifiable(monkeypatch):
    from server import verify_lca_signature

    monkeypatch.setenv("DMRV_HMAC_KEYS", json.dumps({"k1": "secret-one"}))
    monkeypatch.setenv("DMRV_HMAC_ACTIVE_KEY", "k1")
    lca = SimpleNamespace(total=1.0)
    buid = "22222222-2222-2222-2222-222222222222"

    unsigned = SimpleNamespace(
        batch_uuid=buid, lca_signature=None, lca_signature_key_id=None
    )
    assert verify_lca_signature(unsigned, lca) == "unsigned"

    _, secret = hmac_keys.active_key()
    sig = sign_lca_audit(SimpleNamespace(total=1.0), secret, batch_uuid=buid)
    signed_missing_key = SimpleNamespace(
        batch_uuid=buid, lca_signature=sig, lca_signature_key_id="k_gone"
    )
    assert verify_lca_signature(signed_missing_key, lca) == "unverifiable"
