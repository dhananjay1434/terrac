from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64
import json
import pytest
import uuid
from datetime import datetime, timezone
from httpx import AsyncClient
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64

    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit-hcorg")
        session.add(t)
        await session.commit()

    b64_key = TEST_PUBLIC_KEY_B64
    dev_id = "test-device-hcorg"
    payload = {"device_id": dev_id, "public_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit-hcorg"}
    await client.post(
        "/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers
    )

    return {"device_id": dev_id, "b64_key": b64_key}


async def _corroborate_and_create(client, sign_request, dev_id, b64_key, bu, tag):
    """Post canonical telemetry + yield, then create the batch. Returns nothing;
    the batch is left corroborated-but-provisional (no lab H:Corg yet)."""
    tel = {
        "telemetry_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "temperature_readings": [650.0] * 60,
    }
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(tel).encode("utf-8"),
        headers={
            "X-Device-Id": dev_id,
            "X-Idempotency-Key": "op-tel-" + tag,
            "X-Signature": sign_request(
                dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel-" + tag, tel
            ),
        },
    )
    yld = {
        "yield_uuid": str(uuid.uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 1000.0,
    }
    await client.post(
        "/api/v1/yield",
        content=json.dumps(yld).encode("utf-8"),
        headers={
            "X-Device-Id": dev_id,
            "X-Idempotency-Key": "op-yld-" + tag,
            "X-Signature": sign_request(
                dev_id, b64_key, "POST", "/api/v1/yield", "op-yld-" + tag, yld
            ),
        },
    )
    batch = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "harvest_uptime_seconds": 3600,
    }
    resp = await client.post(
        "/api/v1/batches",
        content=json.dumps(batch).encode("utf-8"),
        headers={
            "X-Device-Id": dev_id,
            "X-Idempotency-Key": "op-batch-" + tag,
            "X-Signature": sign_request(
                dev_id, b64_key, "POST", "/api/v1/batches", "op-batch-" + tag, batch
            ),
        },
    )
    assert resp.status_code == 201, resp.text


async def _set_lab_and_read_credit(client, session_factory, bu, ratio):
    """Phase 8-R: lab H:Corg arrives via the authenticated admin channel, not the
    device payload. Returns the recomputed net credit."""
    from sqlalchemy.future import select
    from models import Batch

    r = await client.post(
        "/api/v1/admin/lab-hcorg",
        content=json.dumps({"batch_uuid": bu, "lab_h_corg": ratio}).encode("utf-8"),
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert r.status_code == 200, r.text
    async with session_factory() as s:
        batch = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        return batch.net_credit_t_co2e


async def test_lab_hcorg_passed_to_lca_engine(
    client: AsyncClient, registered_device, session_factory
):
    from tests.remediation.crypto_utils import sign_request

    dev_id = registered_device["device_id"]
    b64_key = registered_device["b64_key"]

    # Low H:Corg (0.1) -> higher stability -> higher credit.
    b1 = str(uuid.uuid4())
    await _corroborate_and_create(client, sign_request, dev_id, b64_key, b1, "low")
    credit_low = await _set_lab_and_read_credit(client, session_factory, b1, 0.1)

    # High H:Corg (0.6) -> lower stability -> lower credit.
    b2 = str(uuid.uuid4())
    await _corroborate_and_create(client, sign_request, dev_id, b64_key, b2, "high")
    credit_high = await _set_lab_and_read_credit(client, session_factory, b2, 0.6)

    assert credit_low > credit_high, (
        f"Credit low {credit_low} should be > credit high {credit_high}"
    )
