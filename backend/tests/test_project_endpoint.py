"""FM-2 — device-facing GET /api/v1/project.

Lets the field app resolve its project's registered feedstock(s) + the
methodology's positive list at runtime, instead of a hard-coded species.
Device-Ed25519-authed (mirrors GET /api/v1/parcels — see
test_parcels_endpoint.py::test_device_parcels_list_returns_approved_only,
the client fixture auto-signs).
"""

from __future__ import annotations

import json

import pytest

from models import Project, RegistryConfig

pytestmark = pytest.mark.asyncio


async def test_get_project_returns_feedstock_and_positive_list(client, session_factory):
    async with session_factory() as session:
        session.add(
            Project(
                project_id="proj-fm2",
                name="FM-2 Project",
                allowed_feedstocks=json.dumps(["Wood_chips"]),
                client_target=10,
            )
        )
        await session.commit()

    resp = await client.get("/api/v1/project?project_id=proj-fm2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["project_id"] == "proj-fm2"
    assert body["name"] == "FM-2 Project"
    assert body["allowed_feedstocks"] == ["Wood_chips"]
    assert body["client_target"] == 10
    assert "Lantana_camara" in body["positive_list"]
    assert "Wood_chips" in body["positive_list"]
    assert "Default" not in body["positive_list"]


async def test_get_project_with_no_feedstock_yet_returns_empty_list(
    client, session_factory
):
    async with session_factory() as session:
        session.add(Project(project_id="proj-fm2-empty", name="No Feedstock Yet"))
        await session.commit()

    resp = await client.get("/api/v1/project?project_id=proj-fm2-empty")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["allowed_feedstocks"] == []
    assert body["client_target"] is None


async def test_get_project_uses_own_registry_config_positive_list(
    client, session_factory
):
    """The positive_list returned reflects THIS project's own resolved
    corg_table (custom RegistryConfig), not the module default."""
    async with session_factory() as session:
        session.add(
            RegistryConfig(
                config_id="cfg-fm2",
                registry_name="FM-2 Registry",
                methodology_version="v1",
                params_json=json.dumps({"corg_table": {"Bamboo": 0.4, "Default": 0.5}}),
            )
        )
        session.add(
            Project(
                project_id="proj-fm2-custom",
                name="Custom Config Project",
                registry_config_id="cfg-fm2",
            )
        )
        await session.commit()

    resp = await client.get("/api/v1/project?project_id=proj-fm2-custom")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["positive_list"] == ["Bamboo"]
    assert "Lantana_camara" not in body["positive_list"]


async def test_get_project_unknown_project_is_404(client):
    resp = await client.get("/api/v1/project?project_id=does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "project_not_found"


async def test_get_project_requires_signature(client):
    """Unsigned request → rejected (device Ed25519 auth, same as batch
    ingest). Mirrors test_parcels_endpoint's equivalent test."""
    resp = await client.get(
        "/api/v1/project?project_id=whatever",
        headers={"X-Device-Id": "some-bogus-device"},
    )
    assert resp.status_code in (401, 403)
