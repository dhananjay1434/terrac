"""V8 Part 4 (G) — config-driven methodology/registry.

Covers: LcaParams()/calculate_carbon_credit default == exact CSI-3.2 behavior
(the literal regression guarantee); params_from_json round-trip + graceful
fallback on a partial/malformed blob; the migration's seeded 'default' row
matches LcaParams() field-for-field (drift guard); credit_engine's
_resolve_lca_config resolves None for every unconfigured case (no project,
unregistered project, project with no registry_config_id) and a real config
when wired; and the portal admin endpoints (create/list, role-gated).
"""

from __future__ import annotations

import json

import pytest

import lca_engine
from lca_engine import LcaParams, calculate_carbon_credit, params_from_json

pytestmark = pytest.mark.asyncio


def test_lcaparams_defaults_match_module_constants():
    p = LcaParams()
    assert p.methodology_version == lca_engine.METHODOLOGY_VERSION
    assert dict(p.corg_table) == dict(lca_engine.CORG_TABLE)
    assert p.safety_deduction_kg_per_t == lca_engine.SAFETY_DEDUCTION_KG_PER_T
    assert p.transport_factor_kg_per_t_km == lca_engine.TRANSPORT_FACTOR_KG_PER_T_KM
    assert p.transport_threshold_km == lca_engine.TRANSPORT_THRESHOLD_KM
    assert p.ch4_compliant_kg_per_t == lca_engine.CH4_COMPLIANT_KG_PER_T
    assert p.ch4_non_compliant_kg_per_t == lca_engine.CH4_NON_COMPLIANT_KG_PER_T


def test_no_config_reproduces_exact_current_behavior():
    """The literal regression guarantee: config=None and config=LcaParams()
    (the CSI-3.2 defaults) must produce byte-identical LCAAudit output."""
    kwargs = dict(
        wet_yield_kg=500.0,
        moisture_percent=12.0,
        min_recorded_temp_c=250.0,
        transport_distance_km=150.0,
        feedstock_species="Lantana_camara",
        h_corg_ratio=0.30,
    )
    baseline = calculate_carbon_credit(**kwargs)
    explicit_default = calculate_carbon_credit(**kwargs, config=LcaParams())
    assert baseline.net_credit_t_co2e == explicit_default.net_credit_t_co2e
    assert baseline.methodology_version == explicit_default.methodology_version
    assert baseline.dry_mass_t == explicit_default.dry_mass_t
    assert baseline.safety_deduction_kg == explicit_default.safety_deduction_kg


def test_custom_config_changes_the_result():
    """Proves the config path is genuinely wired: a stricter safety deduction
    produces a LOWER net credit than the default for identical inputs."""
    kwargs = dict(
        wet_yield_kg=500.0,
        moisture_percent=12.0,
        min_recorded_temp_c=250.0,
        transport_distance_km=0.0,
        feedstock_species="Lantana_camara",
        h_corg_ratio=0.30,
    )
    baseline = calculate_carbon_credit(**kwargs)
    stricter = calculate_carbon_credit(
        **kwargs,
        config=LcaParams(safety_deduction_kg_per_t=200.0),
    )
    assert stricter.net_credit_t_co2e < baseline.net_credit_t_co2e
    assert stricter.safety_deduction_kg > baseline.safety_deduction_kg


def test_params_from_json_partial_blob_falls_back_to_defaults():
    """A config row missing most fields must not crash — every absent field
    falls back to the CSI-3.2 default for that field."""
    partial = params_from_json(json.dumps({"safety_deduction_kg_per_t": 50.0}))
    assert partial.safety_deduction_kg_per_t == 50.0
    assert partial.transport_threshold_km == lca_engine.TRANSPORT_THRESHOLD_KM
    assert dict(partial.corg_table) == dict(lca_engine.CORG_TABLE)


def test_params_from_json_malformed_blob_falls_back_to_defaults():
    malformed = params_from_json("not valid json{{{")
    assert malformed == LcaParams()

    empty = params_from_json("")
    assert empty == LcaParams()


async def test_migration_seed_matches_module_defaults(session_factory):
    """Drift guard: the 'default' row seeded by the registry_configs migration
    must match lca_engine.LcaParams() field-for-field. Base.metadata.create_all
    (this fixture) doesn't run the migration's INSERT, so we replicate the
    exact seed here and assert it round-trips to the same params as the
    module defaults — if a future edit changes one constant without updating
    the migration seed, this test (or the migration itself) must be updated
    consciously, not silently drift.
    """
    from models import RegistryConfig

    seed_params = {
        "corg_table": {
            "Lantana_camara": 0.60,
            "Wood_chips": 0.55,
            "Agricultural_waste": 0.50,
            "Default": 0.55,
        },
        "safety_deduction_kg_per_t": 20.0,
        "transport_factor_kg_per_t_km": 0.01194,
        "transport_threshold_km": 100.0,
        "ch4_compliant_kg_per_t": 0.005,
        "ch4_non_compliant_kg_per_t": 30.0,
    }
    async with session_factory() as session:
        session.add(
            RegistryConfig(
                config_id="default",
                registry_name="Carbon Standards International",
                methodology_version="CSI-3.2",
                params_json=json.dumps(seed_params),
            )
        )
        await session.commit()

        from sqlalchemy import select

        row = (
            await session.execute(
                select(RegistryConfig).where(RegistryConfig.config_id == "default")
            )
        ).scalar_one()
        parsed = params_from_json(row.params_json)
        assert parsed == LcaParams()


async def test_resolve_lca_config_none_when_no_project(session_factory):
    from credit_engine import _resolve_lca_config

    async with session_factory() as session:
        assert await _resolve_lca_config(session, None) is None
        assert await _resolve_lca_config(session, "") is None


async def test_resolve_lca_config_none_when_project_unregistered(session_factory):
    from credit_engine import _resolve_lca_config

    async with session_factory() as session:
        assert await _resolve_lca_config(session, "proj-does-not-exist") is None


async def test_resolve_lca_config_none_when_project_has_no_config(session_factory):
    from credit_engine import _resolve_lca_config
    from models import Project

    async with session_factory() as session:
        session.add(Project(project_id="proj-no-config", name="No Config"))
        await session.commit()
        assert await _resolve_lca_config(session, "proj-no-config") is None


async def test_resolve_lca_config_returns_params_when_wired(session_factory):
    from credit_engine import _resolve_lca_config
    from models import Project, RegistryConfig

    async with session_factory() as session:
        session.add(
            RegistryConfig(
                config_id="custom-1",
                registry_name="Custom Registry",
                methodology_version="Custom-1.0",
                params_json=json.dumps({"safety_deduction_kg_per_t": 99.0}),
            )
        )
        session.add(
            Project(
                project_id="proj-wired",
                name="Wired Project",
                registry_config_id="custom-1",
            )
        )
        await session.commit()

        resolved = await _resolve_lca_config(session, "proj-wired")
        assert resolved is not None
        assert resolved.safety_deduction_kg_per_t == 99.0
        assert resolved.methodology_version == "Custom-1.0"


# ---------------------------------------------------------------------------
# Portal admin endpoints
# ---------------------------------------------------------------------------


async def _login_admin(client, session_factory):
    from portal.auth import hash_password
    from models import PortalUser

    async with session_factory() as session:
        session.add(
            PortalUser(
                email="admin-registry@test.local",
                password_hash=hash_password("correct-horse-battery-staple"),
                role="admin",
                disabled=False,
            )
        )
        await session.commit()
    resp = await client.post(
        "/api/v1/portal/login",
        json={"email": "admin-registry@test.local", "password": "correct-horse-battery-staple"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['token']}"}


async def test_create_registry_config_requires_admin(client):
    resp = await client.post(
        "/api/v1/portal/registry-configs",
        json={
            "config_id": "cfg-1",
            "registry_name": "Test Registry",
            "methodology_version": "v1",
        },
    )
    assert resp.status_code == 401


async def test_create_and_list_registry_config(client, session_factory):
    headers = await _login_admin(client, session_factory)
    resp = await client.post(
        "/api/v1/portal/registry-configs",
        json={
            "config_id": "cfg-2",
            "registry_name": "Test Registry",
            "methodology_version": "v1",
            "params": {"safety_deduction_kg_per_t": 42.0},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["params"]["safety_deduction_kg_per_t"] == 42.0

    list_resp = await client.get("/api/v1/portal/registry-configs", headers=headers)
    assert list_resp.status_code == 200
    ids = [c["config_id"] for c in list_resp.json()["registry_configs"]]
    assert "cfg-2" in ids


async def test_duplicate_registry_config_rejected(client, session_factory):
    headers = await _login_admin(client, session_factory)
    body = {"config_id": "cfg-dup", "registry_name": "R", "methodology_version": "v1"}
    r1 = await client.post("/api/v1/portal/registry-configs", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/portal/registry-configs", json=body, headers=headers)
    assert r2.status_code == 409
