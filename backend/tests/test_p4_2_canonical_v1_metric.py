"""P4.2 — v1 signature-canonical request counter.

Before DMRV_REQUIRE_CANONICAL_V2 can be flipped on, the fleet's remaining v1
traffic must be observable. verify_signature counts every verified request that
used the legacy (unversioned) canonical into dmrv_canonical_v1_requests_total.
"""

import json
import uuid

import pytest

import observability


def _v1_value(route: str) -> float:
    # Read the counter child directly (prometheus_client internal accessor).
    return observability.CANONICAL_V1.labels(route)._value.get()


def test_record_canonical_v1_increments():
    before = _v1_value("/api/v1/test")
    observability.record_canonical_v1("/api/v1/test")
    observability.record_canonical_v1("/api/v1/test")
    assert _v1_value("/api/v1/test") == before + 2


@pytest.mark.asyncio
async def test_v1_signed_request_increments_counter(client, registered_device):
    # The test SignedAsyncClient signs the v1 canonical (no X-Canonical-Version).
    route = "/api/v1/metadata"
    before = _v1_value(route)
    bu = str(uuid.uuid4())
    # A batch must exist for metadata ownership; both go through verify_signature.
    await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": "2026-07-01T00:00:00Z",
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )
    r = await client.post(
        "/api/v1/metadata",
        content=json.dumps({"batch_uuid": bu, "artisan_id": "a"}).encode("utf-8"),
        headers={"X-Idempotency-Key": "meta-" + bu[:8]},
    )
    assert r.status_code == 201
    assert _v1_value(route) == before + 1
