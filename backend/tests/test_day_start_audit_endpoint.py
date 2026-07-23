"""PR-5.1a — device-signed day-start audit create endpoint.

Mirrors test_dispatch_endpoint.py's signed-request helper pattern. OWNER/
OTHER are both pre-enrolled by conftest's autouse fixture with the same
test Ed25519 key (see test_dispatch_endpoint.py's module docstring).
"""

from __future__ import annotations

import json
import uuid

import pytest

from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

OWNER = "test-device-reg"
OTHER = "test-device-1"


def _signed_headers(device_id: str, path: str, op: str, payload: dict) -> dict:
    return {
        "X-Idempotency-Key": op,
        "X-Device-Id": device_id,
        "X-Signature": sign_request(device_id, "", "POST", path, op, payload),
    }


async def _post(client, device_id, op, payload):
    return await client.post(
        "/api/v1/day-start-audits",
        content=json.dumps(payload).encode("utf-8"),
        headers=_signed_headers(device_id, "/api/v1/day-start-audits", op, payload),
    )


def _payload(**over):
    p = {
        "audit_uuid": str(uuid.uuid4()),
        "facility_uuid": "fac-001",
        "audit_date": "2026-07-23",
    }
    p.update(over)
    return p


async def test_create_day_start_audit_happy_path(client):
    payload = _payload(facility_uuid="fac-a")
    r = await _post(client, OWNER, "dsa-a", payload)
    assert r.status_code == 201, r.text
    assert r.json()["audit_uuid"] == payload["audit_uuid"]


async def test_idempotent_same_audit_uuid_repost_is_200(client):
    payload = _payload(facility_uuid="fac-b")
    r1 = await _post(client, OWNER, "dsa-b1", payload)
    assert r1.status_code == 201

    r2 = await _post(client, OWNER, "dsa-b2", payload)
    assert r2.status_code == 200
    assert r2.json()["audit_uuid"] == payload["audit_uuid"]


async def test_second_device_same_facility_and_date_is_409(client):
    payload1 = _payload(facility_uuid="fac-c")
    r1 = await _post(client, OWNER, "dsa-c1", payload1)
    assert r1.status_code == 201

    payload2 = _payload(facility_uuid="fac-c")  # fresh audit_uuid, same slot
    r2 = await _post(client, OTHER, "dsa-c2", payload2)
    assert r2.status_code == 409


async def test_foreign_device_reposting_same_audit_uuid_is_403(client):
    payload = _payload(facility_uuid="fac-d")
    r1 = await _post(client, OWNER, "dsa-d1", payload)
    assert r1.status_code == 201

    r2 = await _post(client, OTHER, "dsa-d2", payload)
    assert r2.status_code == 403
