"""Audit fix 5: tampering the post-signature audit sections
(transport_events / integrity_signals) must be detectable."""

import json
import uuid
from datetime import datetime, timezone

import pytest

from credit_engine import verify_full_audit_hmac

pytestmark = pytest.mark.asyncio


async def _make_batch(client, bu):
    return await client.post(
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
        headers={"X-Idempotency-Key": "op-seal-" + bu[:8]},
    )


async def test_full_audit_hmac_valid_and_tamper_detected(
    client, registered_device, session_factory
):
    from sqlalchemy import select
    from models import Batch

    bu = str(uuid.uuid4())
    r = await _make_batch(client, bu)
    assert r.status_code == 201, r.text

    async with session_factory() as s:
        b = (await s.execute(select(Batch).where(Batch.batch_uuid == bu))).scalar_one()
        assert verify_full_audit_hmac(b.lca_audit_json) == "valid"

        # Tamper an extras section that the dataclass signature does NOT cover.
        audit = json.loads(b.lca_audit_json)
        audit["integrity_signals"]["mock_location_enabled"] = True
        tampered = json.dumps(audit)

    assert verify_full_audit_hmac(tampered) == "invalid"


def test_rows_without_seal_are_unsigned():
    legacy = json.dumps({"methodology_version": "CSI-3.2"})
    assert verify_full_audit_hmac(legacy) == "unsigned"
