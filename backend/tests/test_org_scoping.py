"""V8 Part 5 (D) — multi-tenancy: org-scoped portal users see only their
org's Projects/Facilities/Batches (plus ungrouped/legacy rows); an unscoped
user (org_id NULL — every user before this Part) sees everything, unchanged.

Covers both the pure `tenancy.scope_by_org`/`scope_batches_by_org` query
transforms directly, and the wired-up `/portal/{projects,facilities,batches}`
list endpoints end-to-end.
"""

from __future__ import annotations

import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models import Batch, Facility, Project, PortalUser
from portal.auth import hash_password
import tenancy

pytestmark = pytest.mark.asyncio

_T0 = datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)


async def _login(client, session_factory, *, email, role, org_id=None):
    async with session_factory() as session:
        session.add(
            PortalUser(
                email=email,
                password_hash=hash_password("correct-horse-battery-staple"),
                role=role,
                org_id=org_id,
                disabled=False,
            )
        )
        await session.commit()

    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    token = resp.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_projects(session_factory):
    async with session_factory() as session:
        session.add_all(
            [
                Project(project_id="proj-org-a", name="Org A Project", org_id="org-a"),
                Project(project_id="proj-org-b", name="Org B Project", org_id="org-b"),
                Project(project_id="proj-legacy", name="Legacy Project", org_id=None),
            ]
        )
        await session.commit()


async def _seed_facilities(session_factory):
    async with session_factory() as session:
        session.add_all(
            [
                Facility(
                    facility_uuid=str(_uuid.uuid4()),
                    org_id="org-a",
                    name="Org A Facility",
                    facility_type="artisanal",
                ),
                Facility(
                    facility_uuid=str(_uuid.uuid4()),
                    org_id="org-b",
                    name="Org B Facility",
                    facility_type="artisanal",
                ),
                Facility(
                    facility_uuid=str(_uuid.uuid4()),
                    org_id=None,
                    name="Legacy Facility",
                    facility_type="artisanal",
                ),
            ]
        )
        await session.commit()


def _mk_batch(i: int, *, project=None):
    return Batch(
        batch_uuid=str(_uuid.uuid4()),
        operation_id=f"op-{i}-{_uuid.uuid4().hex[:8]}",
        feedstock_species="Lantana_camara",
        harvest_timestamp=_T0,
        moisture_percent=12.0,
        harvest_uptime_seconds=100,
        status="RECEIVED",
        provisional=False,
        provisional_reasons="[]",
        device_id="dev-A",
        project_id=project,
        received_at=_T0 + timedelta(minutes=i),
    )


async def _seed_batches(session_factory):
    await _seed_projects(session_factory)
    async with session_factory() as session:
        session.add_all(
            [
                _mk_batch(1, project="proj-org-a"),
                _mk_batch(2, project="proj-org-b"),
                _mk_batch(3, project="proj-legacy"),
                _mk_batch(4, project=None),  # no project link at all (pre-Part-0.2 row)
            ]
        )
        await session.commit()


# ---------------------------------------------------------------------------
# Pure tenancy.py — direct query-transform tests (no HTTP).
# ---------------------------------------------------------------------------


async def test_scope_by_org_unscoped_user_sees_everything(session_factory):
    await _seed_projects(session_factory)
    unscoped = PortalUser(id=1, email="a", password_hash="x", role="admin", org_id=None)
    async with session_factory() as session:
        stmt = tenancy.scope_by_org(select(Project), Project.org_id, unscoped)
        rows = (await session.execute(stmt)).scalars().all()
    assert {r.project_id for r in rows} == {"proj-org-a", "proj-org-b", "proj-legacy"}


async def test_scope_by_org_scoped_user_sees_own_plus_legacy(session_factory):
    await _seed_projects(session_factory)
    scoped = PortalUser(id=2, email="b", password_hash="x", role="org_admin", org_id="org-a")
    async with session_factory() as session:
        stmt = tenancy.scope_by_org(select(Project), Project.org_id, scoped)
        rows = (await session.execute(stmt)).scalars().all()
    assert {r.project_id for r in rows} == {"proj-org-a", "proj-legacy"}
    assert "proj-org-b" not in {r.project_id for r in rows}


async def test_scope_batches_by_org_excludes_other_org_and_unresolvable_project(
    session_factory,
):
    await _seed_batches(session_factory)
    scoped = PortalUser(id=3, email="c", password_hash="x", role="org_admin", org_id="org-a")
    async with session_factory() as session:
        stmt = tenancy.scope_batches_by_org(select(Batch), scoped)
        rows = (await session.execute(stmt)).scalars().all()
    projects_seen = {r.project_id for r in rows}
    assert projects_seen == {"proj-org-a", "proj-legacy"}


async def test_scope_batches_by_org_unscoped_user_sees_everything(session_factory):
    await _seed_batches(session_factory)
    unscoped = PortalUser(id=4, email="d", password_hash="x", role="admin", org_id=None)
    async with session_factory() as session:
        stmt = tenancy.scope_batches_by_org(select(Batch), unscoped)
        rows = (await session.execute(stmt)).scalars().all()
    assert len(rows) == 4  # every seeded batch, including the projectless one


# ---------------------------------------------------------------------------
# Wired-up endpoint tests.
# ---------------------------------------------------------------------------


async def test_list_projects_endpoint_scopes_by_org(client, session_factory):
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga@test.local", role="org_admin", org_id="org-a"
    )
    resp = await client.get("/api/v1/portal/projects", headers=headers)
    assert resp.status_code == 200
    ids = {p["project_id"] for p in resp.json()["projects"]}
    assert ids == {"proj-org-a", "proj-legacy"}


async def test_list_facilities_endpoint_scopes_by_org(client, session_factory):
    await _seed_facilities(session_factory)
    headers = await _login(
        client, session_factory, email="orgb@test.local", role="org_admin", org_id="org-b"
    )
    resp = await client.get("/api/v1/portal/facilities", headers=headers)
    assert resp.status_code == 200
    names = {f["name"] for f in resp.json()["facilities"]}
    assert names == {"Org B Facility", "Legacy Facility"}


async def test_list_batches_endpoint_scopes_by_org(client, session_factory):
    await _seed_batches(session_factory)
    headers = await _login(
        client, session_factory, email="orga2@test.local", role="org_admin", org_id="org-a"
    )
    resp = await client.get("/api/v1/portal/batches", headers=headers)
    assert resp.status_code == 200
    projects = {b["project_id"] for b in resp.json()["batches"]}
    assert projects == {"proj-org-a", "proj-legacy"}


async def test_list_projects_endpoint_unscoped_admin_sees_everything(
    client, session_factory
):
    """Regression pin: an admin with no org_id (every admin before this Part)
    must keep seeing every project — tenancy is additive, never a silent
    narrowing of existing behavior."""
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="global-admin@test.local", role="admin"
    )
    resp = await client.get("/api/v1/portal/projects", headers=headers)
    assert resp.status_code == 200
    ids = {p["project_id"] for p in resp.json()["projects"]}
    assert ids == {"proj-org-a", "proj-org-b", "proj-legacy"}
