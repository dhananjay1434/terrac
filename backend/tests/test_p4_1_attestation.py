"""P4.1 — attestation: Play Integrity verdict policy + enforcement grace.

The token->claims decode still needs Google credentials (a human step), so it is
a seam. The POLICY over decoded claims and the grace window that keeps a flag
flip from bricking the enrolled fleet are implemented and tested here.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

import attestation
from attestation import (
    AttestationVerdict,
    attestation_in_grace,
    configure_play_integrity_decoder,
    device_in_grace,
    evaluate_play_integrity_verdict,
    verify_play_integrity,
)
from models import Batch, DeviceKey


_GOOD_CLAIMS = {
    "appIntegrity": {"appRecognitionVerdict": "PLAY_RECOGNIZED"},
    "deviceIntegrity": {"deviceRecognitionVerdict": ["MEETS_DEVICE_INTEGRITY"]},
    "requestDetails": {"requestPackageName": "io.dmrv.dmrv_app", "nonce": "n1"},
}


# --------------------------------------------------------------------------
# Pure verdict policy
# --------------------------------------------------------------------------
def test_valid_verdict_is_verified():
    v = evaluate_play_integrity_verdict(
        _GOOD_CLAIMS, expected_package="io.dmrv.dmrv_app", expected_nonce="n1"
    )
    assert v.verified is True


def test_app_not_recognized_fails():
    claims = {**_GOOD_CLAIMS, "appIntegrity": {"appRecognitionVerdict": "UNRECOGNIZED_VERSION"}}
    v = evaluate_play_integrity_verdict(claims, expected_package="io.dmrv.dmrv_app")
    assert not v.verified and v.reason == "app_not_recognized"


def test_device_integrity_missing_fails():
    claims = {**_GOOD_CLAIMS, "deviceIntegrity": {"deviceRecognitionVerdict": []}}
    v = evaluate_play_integrity_verdict(claims, expected_package="io.dmrv.dmrv_app")
    assert not v.verified and v.reason == "device_integrity_failed"


def test_package_mismatch_fails():
    v = evaluate_play_integrity_verdict(_GOOD_CLAIMS, expected_package="com.evil.app")
    assert not v.verified and v.reason == "package_mismatch"


def test_nonce_mismatch_fails():
    v = evaluate_play_integrity_verdict(
        _GOOD_CLAIMS, expected_package="io.dmrv.dmrv_app", expected_nonce="different"
    )
    assert not v.verified and v.reason == "nonce_mismatch"


def test_malformed_verdict_fails():
    v = evaluate_play_integrity_verdict("not-a-dict", expected_package="x")
    assert not v.verified and v.reason == "malformed_verdict"


# --------------------------------------------------------------------------
# Decoder seam
# --------------------------------------------------------------------------
def test_verify_without_decoder_is_not_configured():
    configure_play_integrity_decoder(None)
    v = verify_play_integrity("tok")
    assert not v.verified and v.reason == "verifier_not_configured"


def test_verify_with_decoder_applies_policy(monkeypatch):
    monkeypatch.setenv("DMRV_PLAY_INTEGRITY_PACKAGE", "io.dmrv.dmrv_app")
    configure_play_integrity_decoder(lambda token: _GOOD_CLAIMS)
    try:
        assert verify_play_integrity("tok", expected_nonce="n1").verified is True
    finally:
        configure_play_integrity_decoder(None)


def test_verify_decoder_error_is_decode_failed():
    def _boom(token):
        raise ValueError("bad token")

    configure_play_integrity_decoder(_boom)
    try:
        v = verify_play_integrity("tok")
        assert not v.verified and v.reason == "decode_failed"
    finally:
        configure_play_integrity_decoder(None)


# --------------------------------------------------------------------------
# Grace predicate
# --------------------------------------------------------------------------
_ENFORCED = datetime(2025, 1, 1, tzinfo=timezone.utc)


def test_preexisting_device_within_window_is_in_grace():
    reg = datetime(2024, 6, 1, tzinfo=timezone.utc)
    now = datetime(2025, 1, 10, tzinfo=timezone.utc)
    assert device_in_grace(reg, now, enforced_since=_ENFORCED, grace_days=30) is True


def test_grace_expires_after_window():
    reg = datetime(2024, 6, 1, tzinfo=timezone.utc)
    now = datetime(2025, 3, 1, tzinfo=timezone.utc)  # > 30 days after enforcement
    assert device_in_grace(reg, now, enforced_since=_ENFORCED, grace_days=30) is False


def test_device_enrolled_after_enforcement_gets_no_grace():
    reg = datetime(2025, 6, 1, tzinfo=timezone.utc)  # after enforced_since
    now = datetime(2025, 6, 2, tzinfo=timezone.utc)
    assert device_in_grace(reg, now, enforced_since=_ENFORCED, grace_days=365) is False


def test_no_grace_when_unconfigured():
    reg = datetime(2024, 6, 1, tzinfo=timezone.utc)
    now = datetime(2025, 1, 10, tzinfo=timezone.utc)
    assert device_in_grace(reg, now, enforced_since=None, grace_days=30) is False
    assert device_in_grace(reg, now, enforced_since=_ENFORCED, grace_days=0) is False
    assert device_in_grace(None, now, enforced_since=_ENFORCED, grace_days=30) is False


def test_attestation_in_grace_reads_env(monkeypatch):
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED_SINCE", "2025-01-01T00:00:00Z")
    monkeypatch.setenv("DMRV_ATTESTATION_GRACE_DAYS", "30")
    reg = datetime(2024, 6, 1, tzinfo=timezone.utc)
    assert attestation_in_grace(reg, datetime(2025, 1, 10, tzinfo=timezone.utc)) is True
    assert attestation_in_grace(reg, datetime(2025, 3, 1, tzinfo=timezone.utc)) is False


# --------------------------------------------------------------------------
# Recompute wiring: grace suppresses the provisional reason, expiry restores it
# --------------------------------------------------------------------------
async def _make_batch(client, bu):
    await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _reasons(session_factory, bu):
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
    return json.loads(b.provisional_reasons or "[]")


async def _set_registered_at(session_factory, device_id, when):
    async with session_factory() as s:
        dev = (
            await s.execute(select(DeviceKey).where(DeviceKey.device_id == device_id))
        ).scalar_one()
        dev.registered_at = when
        await s.commit()


@pytest.mark.asyncio
async def test_grace_suppresses_attestation_reason_for_preexisting_device(
    client, registered_device, session_factory, monkeypatch
):
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED", "1")
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED_SINCE", "2025-01-01T00:00:00Z")
    monkeypatch.setenv("DMRV_ATTESTATION_GRACE_DAYS", "3650")
    monkeypatch.setattr(
        attestation,
        "verify_attestation",
        lambda blob, **k: AttestationVerdict(verified=False, reason="unverified"),
    )
    # Device enrolled BEFORE enforcement began.
    await _set_registered_at(
        session_factory, registered_device["device_id"],
        datetime(2024, 6, 1, tzinfo=timezone.utc),
    )
    bu = str(uuid.uuid4())
    await _make_batch(client, bu)
    assert "attestation_unverified" not in await _reasons(session_factory, bu)


@pytest.mark.asyncio
async def test_no_grace_for_device_enrolled_after_enforcement(
    client, registered_device, session_factory, monkeypatch
):
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED", "1")
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED_SINCE", "2025-01-01T00:00:00Z")
    monkeypatch.setenv("DMRV_ATTESTATION_GRACE_DAYS", "3650")
    monkeypatch.setattr(
        attestation,
        "verify_attestation",
        lambda blob, **k: AttestationVerdict(verified=False, reason="unverified"),
    )
    # Device enrolled AFTER enforcement began → no grace.
    await _set_registered_at(
        session_factory, registered_device["device_id"],
        datetime(2025, 6, 1, tzinfo=timezone.utc),
    )
    bu = str(uuid.uuid4())
    await _make_batch(client, bu)
    assert "attestation_unverified" in await _reasons(session_factory, bu)
