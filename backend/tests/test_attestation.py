"""T2.1 — platform attestation verifier interface + enforcement wiring.

The real Play Integrity / DeviceCheck verifier awaits provider credentials, so a
genuine token returns unverified. These tests inject a verdict double via
monkeypatch to prove the enforcement switch behaves: when
DMRV_ATTESTATION_ENFORCED=1, an unverified batch goes PROVISIONAL with
attestation_unverified; a verified one does not; and with enforcement off
(default) the reason never appears.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

import attestation
from attestation import AttestationVerdict, verify_play_integrity
from models import Batch



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


@pytest.mark.asyncio
async def test_enforced_unverified_batch_is_provisional(
    client, registered_device, session_factory, monkeypatch
):
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED", "1")
    monkeypatch.setattr(
        attestation,
        "verify_attestation",
        lambda blob, **k: AttestationVerdict(verified=False, reason="test_forged"),
    )
    bu = str(uuid.uuid4())
    await _make_batch(client, bu)
    assert "attestation_unverified" in await _reasons(session_factory, bu)


@pytest.mark.asyncio
async def test_enforced_verified_batch_clears_reason(
    client, registered_device, session_factory, monkeypatch
):
    monkeypatch.setenv("DMRV_ATTESTATION_ENFORCED", "1")
    monkeypatch.setattr(
        attestation,
        "verify_attestation",
        lambda blob, **k: AttestationVerdict(verified=True),
    )
    bu = str(uuid.uuid4())
    await _make_batch(client, bu)
    assert "attestation_unverified" not in await _reasons(session_factory, bu)


@pytest.mark.asyncio
async def test_disabled_by_default_never_gates(
    client, registered_device, session_factory, monkeypatch
):
    # No DMRV_ATTESTATION_ENFORCED -> off. Even an unverified verdict is inert.
    monkeypatch.setattr(
        attestation,
        "verify_attestation",
        lambda blob, **k: AttestationVerdict(verified=False, reason="test_forged"),
    )
    bu = str(uuid.uuid4())
    await _make_batch(client, bu)
    assert "attestation_unverified" not in await _reasons(session_factory, bu)


def test_play_integrity_stub_is_unverified_until_configured():
    v = verify_play_integrity("some-token", expected_nonce="n")
    assert v.verified is False
    assert v.reason == "verifier_not_configured"
