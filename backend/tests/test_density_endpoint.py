"""Deferred R3 — device-signed density-test submission endpoint.

Covers the gap F's admin-only bulk-density-tests route left for the field:
a device (Ed25519-signed, not a portal-authenticated human) submitting a
mass/volume calibration reading, with the SERVER computing and storing the
authoritative density — never trusting a client-supplied value.
"""

from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import select

from models import BulkDensityTest
from tests.remediation.crypto_utils import sign_request

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"
OTHER_DEVICE = "test-device-1"


def _signed_headers(device_id: str, path: str, op: str, payload: dict) -> dict:
    return {
        "X-Idempotency-Key": op,
        "X-Device-Id": device_id,
        "X-Signature": sign_request(device_id, "", "POST", path, op, payload),
    }


async def _post(client, device_id, path, op, payload):
    return await client.post(
        path,
        content=json.dumps(payload).encode("utf-8"),
        headers=_signed_headers(device_id, path, op, payload),
    )


def _payload(test_uuid, **over):
    p = {
        "test_uuid": test_uuid,
        "project_id": "proj-density-1",
        "mass_kg": 50.0,
        "volume_l": 200.0,
    }
    p.update(over)
    return p


async def test_server_computes_density_from_mass_and_volume(client, session_factory):
    tu = str(uuid.uuid4())
    resp = await _post(
        client, DEVICE, "/api/v1/density-tests", "dens-1", _payload(tu)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["test_uuid"] == tu
    assert body["density_kg_per_l"] == pytest.approx(0.25)

    async with session_factory() as session:
        row = (
            await session.execute(
                select(BulkDensityTest).where(BulkDensityTest.test_uuid == tu)
            )
        ).scalar_one()
        assert row.density_kg_per_l == pytest.approx(0.25)
        assert row.project_id == "proj-density-1"
        assert row.mass_kg == 50.0
        assert row.volume_l == 200.0
        # Deferred R3 scope: no explicit expiry UX yet — always NULL, which
        # the C10 gate already treats as fail-closed (not in-date).
        assert row.valid_until is None
        # PR-6.2 prerequisite: device_id is now persisted so density_video
        # media can be ownership-checked.
        assert row.device_id == DEVICE


async def test_foreign_device_reposting_same_test_uuid_is_403(client):
    tu = str(uuid.uuid4())
    r1 = await _post(client, DEVICE, "/api/v1/density-tests", "dens-owner-1", _payload(tu))
    assert r1.status_code == 201

    r2 = await _post(
        client, OTHER_DEVICE, "/api/v1/density-tests", "dens-owner-2", _payload(tu)
    )
    assert r2.status_code == 403


async def test_client_supplied_density_is_ignored_if_present(client):
    """extra='forbid' on the schema means a client-supplied density_kg_per_l
    is REJECTED outright (422), not silently overridden — proving there is
    no path for a client value to reach storage."""
    tu = str(uuid.uuid4())
    payload = _payload(tu)
    payload["density_kg_per_l"] = 999.0
    resp = await _post(client, DEVICE, "/api/v1/density-tests", "dens-2", payload)
    assert resp.status_code == 422


async def test_duplicate_test_uuid_is_idempotent_noop(client, session_factory):
    tu = str(uuid.uuid4())
    first = await _post(
        client, DEVICE, "/api/v1/density-tests", "dens-3a", _payload(tu)
    )
    assert first.status_code == 201

    second = await _post(
        client,
        DEVICE,
        "/api/v1/density-tests",
        "dens-3b",
        _payload(tu, mass_kg=999.0, volume_l=1.0),  # different inputs, same uuid
    )
    assert second.status_code == 201
    assert second.json()["density_kg_per_l"] == pytest.approx(0.25)  # unchanged

    async with session_factory() as session:
        rows = (
            await session.execute(
                select(BulkDensityTest).where(BulkDensityTest.test_uuid == tu)
            )
        ).scalars().all()
        assert len(rows) == 1


async def test_zero_volume_rejected(client):
    resp = await _post(
        client,
        DEVICE,
        "/api/v1/density-tests",
        "dens-4",
        _payload(str(uuid.uuid4()), volume_l=0.0),
    )
    assert resp.status_code == 422  # Pydantic gt=0.0


async def test_negative_mass_rejected(client):
    resp = await _post(
        client,
        DEVICE,
        "/api/v1/density-tests",
        "dens-5",
        _payload(str(uuid.uuid4()), mass_kg=-10.0),
    )
    assert resp.status_code == 422  # Pydantic gt=0.0


async def test_missing_project_id_rejected(client):
    payload = _payload(str(uuid.uuid4()))
    del payload["project_id"]
    resp = await _post(client, DEVICE, "/api/v1/density-tests", "dens-6", payload)
    assert resp.status_code == 422
