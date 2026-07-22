"""V8 Part 2 — farmer registration ENDPOINT tests (routers/farmers.py).

The existing test_farmer_models.py is ORM-only and never exercised the router,
where the real defects lived: a swallowed IntegrityError that returned a false
"success", non-atomic farmer+children writes, and unvalidated "masked_*" payment
fields. These drive the signed device endpoint end-to-end via the `client`
fixture (SignedAsyncClient auto-signs; `registered_device` enrolls the key).
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from models import Farmer, FarmerDocument, FarmerPayment

pytestmark = pytest.mark.asyncio


def _farmer_payload(**over):
    p = {
        "farmer_uuid": str(uuid.uuid4()),
        "project_id": "proj-farmers",
        "first_name": "Asha",
        "mobile_number": "9990001111",
        "documents": [],
        "payments": [],
        "consents": [],
    }
    p.update(over)
    return p


async def _post_farmer(client, payload, op=None):
    op = op or ("f-" + payload["farmer_uuid"][:8])
    return await client.post(
        "/api/v1/farmers",
        json=payload,
        headers={"X-Idempotency-Key": op},
    )


async def test_create_farmer(client, registered_device):
    resp = await _post_farmer(client, _farmer_payload())
    assert resp.status_code == 201, resp.text
    assert resp.json()["status"] == "success"


async def test_mobile_uniqueness_rejected(client, registered_device, session_factory):
    p1 = _farmer_payload(mobile_number="8887776666")
    r1 = await _post_farmer(client, p1)
    assert r1.status_code == 201

    # Different farmer_uuid, SAME project + mobile → 409.
    p2 = _farmer_payload(mobile_number="8887776666")
    r2 = await _post_farmer(client, p2)
    assert r2.status_code == 409
    assert "mobile" in r2.json()["detail"].lower()

    # Exactly one farmer with that mobile persisted (no partial/false-success row).
    async with session_factory() as session:
        n = (
            await session.execute(
                select(func.count())
                .select_from(Farmer)
                .where(Farmer.mobile_number == "8887776666")
            )
        ).scalar()
        assert n == 1


async def test_unmasked_account_rejected(client, registered_device):
    """PII guard: a full (unmasked) account number in a masked_* field is 422,
    not silently stored in plaintext."""
    payload = _farmer_payload(
        payments=[
            {
                "rail": "bank",
                "account_holder": "Asha Devi",
                "masked_account": "123456789012",  # full number, no mask char
                "ifsc_code": "HDFC0001234",
            }
        ]
    )
    resp = await _post_farmer(client, payload)
    assert resp.status_code == 422


async def test_masked_account_accepted(client, registered_device):
    payload = _farmer_payload(
        payments=[
            {
                "rail": "bank",
                "account_holder": "Asha Devi",
                "masked_account": "XXXXXXXX9012",  # properly masked
                "ifsc_code": "HDFC0001234",
            }
        ]
    )
    resp = await _post_farmer(client, payload)
    assert resp.status_code == 201, resp.text


async def test_idempotent_retry_does_not_duplicate_children(
    client, registered_device, session_factory
):
    """An offline outbox retry (same farmer_uuid) must upsert, not accumulate
    duplicate document rows."""
    fid = str(uuid.uuid4())
    payload = _farmer_payload(
        farmer_uuid=fid,
        documents=[{"doc_type": "aadhaar", "last4": "1234", "media_id": "m1"}],
    )
    r1 = await _post_farmer(client, payload, op="f-retry")
    assert r1.status_code == 201
    r2 = await _post_farmer(client, payload, op="f-retry")
    assert r2.status_code == 200  # existing → update path

    async with session_factory() as session:
        docs = (
            await session.execute(
                select(func.count())
                .select_from(FarmerDocument)
                .where(FarmerDocument.farmer_uuid == fid)
            )
        ).scalar()
        assert docs == 1  # not 2 — children were replaced, not duplicated


async def test_app_shaped_payload_is_accepted(client, registered_device, session_factory):
    """Contract: the exact payload the app's insertFarmerWithOutbox emits —
    masked bank payment, a consent with ONLY exclusivity_ack, and no documents
    (media deferred) — must validate and persist end-to-end."""
    fid = str(uuid.uuid4())
    payload = _farmer_payload(
        farmer_uuid=fid,
        first_name="Asha",
        mobile_number="9995550000",
        village="Rampur",
        kyc_status="self_declared",
        consent_status="acknowledged",
        documents=[],
        payments=[
            {
                "rail": "bank",
                "account_holder": "Asha Devi",
                "masked_account": "XXXXXXXX9012",
                "ifsc_code": "HDFC0001234",
            }
        ],
        consents=[{"exclusivity_ack": True}],
    )
    resp = await _post_farmer(client, payload)
    assert resp.status_code == 201, resp.text

    # Detail (portal shape) reflects the masked payment + consent.
    async with session_factory() as session:
        from models import FarmerPayment, FarmerConsent
        from sqlalchemy import select as _select

        pay = (
            await session.execute(
                _select(FarmerPayment).where(FarmerPayment.farmer_uuid == fid)
            )
        ).scalar_one()
        assert pay.masked_account == "XXXXXXXX9012"
        cons = (
            await session.execute(
                _select(FarmerConsent).where(FarmerConsent.farmer_uuid == fid)
            )
        ).scalar_one()
        assert cons.exclusivity_ack is True


async def test_last4_only_for_documents(client, registered_device):
    """Document identifiers are last-4 only — a full Aadhaar cannot fit the
    4-char field (schema-enforced), so KYC PII is minimized at the boundary."""
    payload = _farmer_payload(
        documents=[{"doc_type": "aadhaar", "last4": "123456789012", "media_id": "m"}]
    )
    resp = await _post_farmer(client, payload)
    assert resp.status_code == 422
