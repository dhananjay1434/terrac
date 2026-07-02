"""Phase 11 — strict schemas + size bounds on the evidence endpoints.

/telemetry, /yield, /metadata, /application used to accept a raw dict with no
schema and no size cap. They now use extra="forbid" models with bounded lists.
This pins: unknown keys → 422; oversized array → 422; a valid minimal payload
→ 201 and persists.
"""

import json
from uuid import uuid4

import pytest

pytestmark = pytest.mark.asyncio

# (endpoint, valid minimal payload)
_VALID = {
    "/api/v1/telemetry": lambda bu: {
        "telemetry_uuid": str(uuid4()),
        "batch_uuid": bu,
        "temperature_readings": [650.0] * 60,
    },
    "/api/v1/yield": lambda bu: {
        "yield_uuid": str(uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 120.0,
    },
    "/api/v1/metadata": lambda bu: {
        "batch_uuid": bu,
        "artisan_id": "art-1",
    },
    "/api/v1/application": lambda bu: {
        "application_uuid": str(uuid4()),
        "batch_uuid": bu,
        "latitude": 12.9,
        "longitude": 77.5,
    },
}


async def _post(client, endpoint, payload, key):
    return await client.post(
        endpoint,
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": key},
    )


@pytest.mark.parametrize("endpoint", list(_VALID))
async def test_valid_minimal_payload_accepted(client, registered_device, endpoint):
    bu = str(uuid4())
    r = await _post(client, endpoint, _VALID[endpoint](bu), "ok-" + bu[:8])
    assert r.status_code == 201, r.text


@pytest.mark.parametrize("endpoint", list(_VALID))
async def test_unknown_field_rejected(client, registered_device, endpoint):
    bu = str(uuid4())
    payload = _VALID[endpoint](bu)
    payload["definitely_not_a_field"] = "x"
    r = await _post(client, endpoint, payload, "extra-" + bu[:8])
    assert r.status_code == 422, r.text


async def test_oversized_temperature_array_rejected(client, registered_device):
    bu = str(uuid4())
    payload = {
        "telemetry_uuid": str(uuid4()),
        "batch_uuid": bu,
        "temperature_readings": [650.0] * 100_001,  # exceeds max_length=100_000
    }
    r = await _post(client, "/api/v1/telemetry", payload, "big-" + bu[:8])
    assert r.status_code == 422, r.text


async def test_overlong_string_field_rejected(client, registered_device):
    # Phase 11-R: free-text fields are length-bounded (artisan_id max_length=128).
    bu = str(uuid4())
    payload = {"batch_uuid": bu, "artisan_id": "x" * 10_000}
    r = await _post(client, "/api/v1/metadata", payload, "str-" + bu[:8])
    assert r.status_code == 422, r.text


async def test_oversized_wet_yield_rejected(client, registered_device):
    # Phase 15-C: a single self-asserted yield field can't be arbitrarily large.
    bu = str(uuid4())
    payload = {
        "yield_uuid": str(uuid4()),
        "batch_uuid": bu,
        "wet_yield_weight_kg": 1_000_000_000.0,  # 1e9 kg — absurd
    }
    r = await _post(client, "/api/v1/yield", payload, "wy-" + bu[:8])
    assert r.status_code == 422, r.text


async def test_kiln_type_persists_and_is_validated(
    client, registered_device, session_factory
):
    # Rainbow C0: kiln_type is an optional open|closed enum, persisted in payload_json.
    from models import PyrolysisTelemetry
    from sqlalchemy.future import select

    bu = str(uuid4())
    tu = str(uuid4())
    r = await _post(
        client,
        "/api/v1/telemetry",
        {"telemetry_uuid": tu, "batch_uuid": bu, "kiln_type": "open", "kiln_id": "K-1"},
        "kt-" + bu[:8],
    )
    assert r.status_code == 201, r.text
    async with session_factory() as s:
        row = (
            await s.execute(
                select(PyrolysisTelemetry).where(
                    PyrolysisTelemetry.telemetry_uuid == tu
                )
            )
        ).scalar_one()
    assert json.loads(row.payload_json)["kiln_type"] == "open"

    # Invalid enum value is rejected.
    bad = await _post(
        client,
        "/api/v1/telemetry",
        {
            "telemetry_uuid": str(uuid4()),
            "batch_uuid": str(uuid4()),
            "kiln_type": "banana",
        },
        "kt-bad",
    )
    assert bad.status_code == 422, bad.text


async def test_out_of_range_temperature_sample_rejected(client, registered_device):
    # Phase 15-C: per-value temperature bound; one absurd reading rejects the batch.
    bu = str(uuid4())
    payload = {
        "telemetry_uuid": str(uuid4()),
        "batch_uuid": bu,
        "temperature_readings": [650.0] * 59 + [9999.0],  # one impossible sample
    }
    r = await _post(client, "/api/v1/telemetry", payload, "tr-" + bu[:8])
    assert r.status_code == 422, r.text


async def test_oversized_request_body_rejected_413(client, registered_device):
    # Phase 11-R: Content-Length over the JSON cap (2 MB) is rejected before parsing.
    # Build a well-shaped telemetry body just over the cap via a big smoke_evidence blob.
    bu = str(uuid4())
    big = [
        {"stage": "s", "sha256": "a" * 4000} for _ in range(700)
    ]  # > 2 MB serialized
    payload = {"telemetry_uuid": str(uuid4()), "batch_uuid": bu, "smoke_evidence": big}
    r = await _post(client, "/api/v1/telemetry", payload, "413-" + bu[:8])
    assert r.status_code == 413, f"expected 413, got {r.status_code}"
