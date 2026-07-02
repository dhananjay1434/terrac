"""Rainbow compliance C5 — delivery record + buyer/end-user identity.

Four optional fields on the /application payload (delivery_date,
delivered_amount_kg, buyer_name, buyer_contact), persisted in payload_json. The
deriver is inert by default (enforced at the C10 unified gate), so posting them
must round-trip and must NOT gate issuance today; the enforced logic is
unit-tested directly.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.future import select

from models import Batch, EndUseApplication
from corroboration import derive_delivery_compliance
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

OWNER = "test-device-reg"


def test_deriver_inert_by_default():
    # Even with an empty payload, not enforced -> both signals pass.
    assert derive_delivery_compliance(None) == (True, True)
    assert derive_delivery_compliance({}) == (True, True)


def test_deriver_enforced_flags_missing_pieces():
    # Nothing captured -> both fail.
    assert derive_delivery_compliance({}, enforced=True) == (False, False)
    # Delivery present (amount), buyer missing.
    assert derive_delivery_compliance({"delivered_amount_kg": 50.0}, enforced=True) == (
        True,
        False,
    )
    # Delivery date counts as a delivery record; buyer name present.
    assert derive_delivery_compliance(
        {"delivery_date": "2026-07-02T00:00:00Z", "buyer_name": "Asha"},
        enforced=True,
    ) == (True, True)
    # Whitespace-only buyer name does not count.
    assert derive_delivery_compliance(
        {"delivery_date": "x", "buyer_name": "   "}, enforced=True
    ) == (True, False)


async def _post(client, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers={
            "X-Idempotency-Key": op,
            "X-Device-Id": OWNER,
            "X-Signature": sign_request(OWNER, "", "POST", path, op, payload),
        },
    )


async def _create_batch(client, bu):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    r = await _post(client, "/api/v1/batches", "b-" + bu[:8], payload)
    assert r.status_code == 201, r.text


async def test_application_with_buyer_delivery_round_trips_and_is_inert(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    p = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "delivery_date": "2026-07-02T10:00:00Z",
        "delivered_amount_kg": 42.5,
        "buyer_name": "Asha Farmer Collective",
        "buyer_contact": "+91-99999-00000",
    }
    r = await _post(client, "/api/v1/application", "app-" + bu[:6], p)
    assert r.status_code == 201, r.text

    async with session_factory() as s:
        row = (
            await s.execute(
                select(EndUseApplication).where(EndUseApplication.batch_uuid == bu)
            )
        ).scalar_one()
        stored = json.loads(row.payload_json)
        assert stored["buyer_name"] == "Asha Farmer Collective"
        assert stored["delivered_amount_kg"] == 42.5
        assert stored["buyer_contact"] == "+91-99999-00000"

        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        reasons = json.loads(batch.provisional_reasons or "[]")
        # Inert by default — C5 must NOT gate issuance yet.
        assert "missing_delivery_record" not in reasons
        assert "missing_buyer_identity" not in reasons


async def test_buyer_contact_over_length_is_rejected(client, registered_device):
    bu = str(uuid.uuid4())
    await _create_batch(client, bu)
    p = {
        "application_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "buyer_contact": "x" * 300,  # > 256 max_length
    }
    r = await _post(client, "/api/v1/application", "app-len-" + bu[:6], p)
    assert r.status_code == 422, r.text
