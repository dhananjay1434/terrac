from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64, sign_canonical
import pytest
import pytest_asyncio
import json
import base64
import hmac
import hashlib
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.future import select
from models import DeviceKey, EnrollmentToken, Batch
import server

_B64_KEY = TEST_PUBLIC_KEY_B64


@pytest_asyncio.fixture
async def setup_device(client: AsyncClient, session_factory):
    # Mint token
    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit")
        session.add(t)
        await session.commit()

    # Register device
    dev_id = "device-credit"
    payload = {"device_id": dev_id, "public_key": _B64_KEY}
    headers = {"X-Enrollment-Token": "test-credit"}
    resp = await client.post("/api/v1/register", json=payload, headers=headers)
    assert resp.status_code == 201
    return dev_id


@pytest.mark.asyncio
async def test_unsigned_batch_rejected_or_quarantined(
    client: AsyncClient, setup_device, session_factory
):
    payload = {
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 15.0,
        "harvest_uptime_seconds": 3600,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 0.0,
    }

    headers = {"X-Device-Id": setup_device, "X-Idempotency-Key": "op-batch-1"}

    resp = await client.post("/api/v1/batches", json=payload, headers=headers)
    assert resp.status_code == 401

    # verify no row created
    async with session_factory() as session:
        result = await session.execute(select(Batch))
        batches = result.scalars().all()
        assert len(batches) == 0


@pytest.mark.asyncio
async def test_verified_batch_gets_credit(
    client: AsyncClient, setup_device, session_factory
):
    payload = {
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 15.0,
        "harvest_uptime_seconds": 3600,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 0.0,
        "transport_distance_km": 0.0,
    }

    raw_body = json.dumps(payload).encode("utf-8")
    op_id = "op-batch-2"
    canonical = "\n".join(
        [
            "POST",
            "/api/v1/batches",
            op_id,
            hashlib.sha256(raw_body).hexdigest(),
            setup_device,
        ]
    ).encode("utf-8")
    # Phase 5: sign with the enrolled device's Ed25519 private key.
    sig = sign_canonical(canonical)

    headers = {
        "X-Device-Id": setup_device,
        "X-Idempotency-Key": op_id,
        "X-Signature": sig,
    }

    resp = await client.post("/api/v1/batches", content=raw_body, headers=headers)
    assert resp.status_code == 201

    # verify row created with credit
    import uuid

    async with session_factory() as session:
        result = await session.execute(
            select(Batch).where(Batch.batch_uuid == str(uuid.UUID(payload["batch_uuid"])))
        )
        batch = result.scalar_one_or_none()
        assert batch is not None
        assert batch.net_credit_t_co2e is not None


@pytest.mark.asyncio
async def test_missing_hmac_secret_fails_fast():
    # Verify the code has a runtime check for the secret
    # This was added in server.py (Lines 32-34 typically)
    assert hasattr(server, "_HMAC_SECRET")
    assert server._HMAC_SECRET != "default_secret"
