"""P2.2 — device-facing GET /api/v1/kiln.

Lets the field app resolve a kiln's DECLARED sensor_profile (+ type) so the
burn UI can pick the right telemetry view. Device-Ed25519-authed, read-only —
mirrors GET /api/v1/project (test_project_endpoint.py); the client fixture
auto-signs. The profile is a declared EXPECTATION, never a source of live
channels (Global Rule 10 / audit fix #1).
"""

from __future__ import annotations

import pytest

from models import Kiln

pytestmark = pytest.mark.asyncio


async def test_get_kiln_returns_sensor_profile(client, session_factory):
    async with session_factory() as session:
        session.add(
            Kiln(kiln_id="KILN-P22", kiln_type="open", sensor_profile="full")
        )
        await session.commit()

    resp = await client.get("/api/v1/kiln?kiln_id=KILN-P22")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["kiln_id"] == "KILN-P22"
    assert body["sensor_profile"] == "full"
    assert body["kiln_type"] == "open"


async def test_get_kiln_unknown_kiln_is_404(client):
    resp = await client.get("/api/v1/kiln?kiln_id=does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "kiln_not_found"


async def test_get_kiln_requires_signature(client):
    """Unsigned request → rejected (device Ed25519 auth, same as batch
    ingest). Mirrors test_project_endpoint's equivalent test."""
    resp = await client.get(
        "/api/v1/kiln?kiln_id=whatever",
        headers={"X-Device-Id": "some-bogus-device"},
    )
    assert resp.status_code in (401, 403)
