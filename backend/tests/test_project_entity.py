"""V8 Part 0.2 — Project entity: API-level tests.

Covers create, role-gating, duplicate-create rejection (the concurrency
primitive is the project_id PK's unique constraint — see routes.create_project),
and that Batch/AnnualVerification resolve their project by value (no DB-enforced
FK; see models.Project docstring). The real Alembic backfill migration is
covered separately in test_project_entity_migration.py (drives the actual
upgrade/downgrade against a throwaway SQLite file, not just ORM create_all).
"""

from __future__ import annotations

import json
import uuid as _uuid

import pytest
from sqlalchemy import select

from models import AnnualVerification, Batch, Project

pytestmark = pytest.mark.asyncio


async def _login_admin(client, session_factory):
    """Seed an admin PortalUser + return a Bearer header, mirroring the
    pattern other portal tests use (test_portal_auth.py)."""
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": "admin@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_create_project_requires_admin_role(client):
    resp = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-1", "name": "Project One"},
    )
    assert resp.status_code == 401


async def test_create_and_list_project(client, session_factory):
    headers = await _login_admin(client, session_factory)

    resp = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-1", "name": "Project One"},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["project_id"] == "proj-1"
    assert body["name"] == "Project One"
    assert body["status"] == "active"

    list_resp = await client.get("/api/v1/portal/projects", headers=headers)
    assert list_resp.status_code == 200
    ids = [p["project_id"] for p in list_resp.json()["projects"]]
    assert "proj-1" in ids


async def test_duplicate_project_id_rejected(client, session_factory):
    """The concurrency-safety primitive: project_id is a PK, so a second
    create with the same id can never silently succeed as a duplicate row —
    it always 409s, regardless of timing."""
    headers = await _login_admin(client, session_factory)

    first = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-dup", "name": "First"},
        headers=headers,
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-dup", "name": "Second attempt"},
        headers=headers,
    )
    assert second.status_code == 409

    # Exactly one row exists — the rejected attempt left no partial/duplicate state.
    async with session_factory() as session:
        rows = (
            await session.execute(
                select(Project).where(Project.project_id == "proj-dup")
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].name == "First"


async def test_create_project_with_valid_feedstock_and_client_target_roundtrips(
    client, session_factory
):
    """FM-1: allowed_feedstocks (validated against the module default
    positive list, since no registry_config_id is set) and client_target
    round-trip through create + the response body."""
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/projects",
        json={
            "project_id": "proj-feedstock",
            "name": "Feedstock Project",
            "allowed_feedstocks": ["Wood_chips"],
            "client_target": 25,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["allowed_feedstocks"] == ["Wood_chips"]
    assert body["client_target"] == 25


async def test_create_project_with_unknown_feedstock_rejected(client, session_factory):
    """FM-1: a species not in the resolved positive list is rejected at
    registration — the guardrail against the FM-0 silent-default bug."""
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/projects",
        json={
            "project_id": "proj-bad-feedstock",
            "name": "Bad Feedstock Project",
            "allowed_feedstocks": ["Not_a_real_species"],
        },
        headers=headers,
    )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["error"] == "feedstock_not_in_positive_list"
    assert "Not_a_real_species" in detail["unknown"]

    async with session_factory() as session:
        rows = (
            await session.execute(
                select(Project).where(Project.project_id == "proj-bad-feedstock")
            )
        ).scalars().all()
        assert rows == []  # rejected before persist — no partial row


async def test_create_project_with_empty_feedstock_list_allowed(
    client, session_factory
):
    """Grandfather: a project may be registered before its feedstock is
    decided — empty allowed_feedstocks is valid, not an error."""
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-no-feedstock-yet", "name": "TBD Project"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["allowed_feedstocks"] == []
    assert resp.json()["client_target"] is None


async def test_create_project_feedstock_validated_against_own_registry_config(
    client, session_factory
):
    """A project pointed at a RegistryConfig with a CUSTOM corg_table is
    validated against THAT table, not the module default — proves the
    per-project positive list (not _resolve_lca_config, which would return
    None for a not-yet-persisted project) is what's actually checked."""
    from models import RegistryConfig

    async with session_factory() as session:
        session.add(
            RegistryConfig(
                config_id="cfg-custom-feedstock",
                registry_name="Custom Registry",
                methodology_version="v1",
                params_json=json.dumps({"corg_table": {"Bamboo": 0.45, "Default": 0.5}}),
            )
        )
        await session.commit()

    headers = await _login_admin(client, session_factory)
    ok = await client.post(
        "/api/v1/portal/projects",
        json={
            "project_id": "proj-custom-feedstock",
            "name": "Custom Feedstock Project",
            "registry_config_id": "cfg-custom-feedstock",
            "allowed_feedstocks": ["Bamboo"],
        },
        headers=headers,
    )
    assert ok.status_code == 201, ok.text

    rejected = await client.post(
        "/api/v1/portal/projects",
        json={
            "project_id": "proj-custom-feedstock-2",
            "name": "Custom Feedstock Project 2",
            "registry_config_id": "cfg-custom-feedstock",
            # Lantana_camara is in the MODULE default table but NOT in this
            # project's own custom corg_table — must be rejected.
            "allowed_feedstocks": ["Lantana_camara"],
        },
        headers=headers,
    )
    assert rejected.status_code == 422


async def test_extra_field_rejected(client, session_factory):
    """model_config = extra='forbid' on ProjectCreate — schema boundary discipline."""
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-x", "name": "X", "not_a_real_field": 1},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_batch_resolves_its_project_by_value(
    client, session_factory, registered_device
):
    """No DB-enforced FK (by design) — but once a Project row exists with the
    same project_id a batch already carries, an application-level lookup
    resolves it. This is the exact 'batch resolves its project' guarantee the
    blueprint calls for."""
    headers = await _login_admin(client, session_factory)
    await client.post(
        "/api/v1/portal/projects",
        json={"project_id": "proj-batch-link", "name": "Linked Project"},
        headers=headers,
    )

    batch_uuid = str(_uuid.uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-07-01T10:00:00+05:30",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "project_id": "proj-batch-link",
    }
    post_resp = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "proj-link-" + batch_uuid[:8]},
    )
    assert post_resp.status_code in (200, 201)

    async with session_factory() as session:
        batch = (
            await session.execute(select(Batch).where(Batch.batch_uuid == batch_uuid))
        ).scalar_one()
        project = (
            await session.execute(
                select(Project).where(Project.project_id == batch.project_id)
            )
        ).scalar_one_or_none()
        assert project is not None
        assert project.name == "Linked Project"


async def test_batch_with_unregistered_project_id_does_not_break(
    client, session_factory
):
    """Grandfather / offline-first: a batch can arrive with a project_id that
    has no Project row yet (device synced before the portal registered the
    project). This must NOT fail — the DB-enforced-FK approach was rejected
    for exactly this reason (models.Project docstring)."""
    batch_uuid = str(_uuid.uuid4())
    payload = {
        "batch_uuid": batch_uuid,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-07-01T10:00:00+05:30",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "project_id": "proj-not-yet-registered",
    }
    post_resp = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "proj-unreg-" + batch_uuid[:8]},
    )
    assert post_resp.status_code in (200, 201)

    async with session_factory() as session:
        project = (
            await session.execute(
                select(Project).where(Project.project_id == "proj-not-yet-registered")
            )
        ).scalar_one_or_none()
        assert project is None  # no row — and nothing above raised for that.


async def test_annual_verification_resolves_its_project(session_factory):
    async with session_factory() as session:
        session.add(
            Project(project_id="proj-annual", name="Annual Verif Project")
        )
        session.add(
            AnnualVerification(
                project_id="proj-annual",
                year=2026,
                payload_json="{}",
            )
        )
        await session.commit()

        av = (
            await session.execute(
                select(AnnualVerification).where(
                    AnnualVerification.project_id == "proj-annual"
                )
            )
        ).scalar_one()
        project = (
            await session.execute(
                select(Project).where(Project.project_id == av.project_id)
            )
        ).scalar_one_or_none()
        assert project is not None
        assert project.name == "Annual Verif Project"
