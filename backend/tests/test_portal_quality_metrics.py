"""Part 1F.1 -- GET /api/v1/portal/metrics/quality.

Org-scoped, read-only pyrolysis + permanence quality aggregates. Covers:
  - Real compute flow: telemetry peak/pct-above-threshold and permanence_pct
    are derived from genuine corroborated/labbed batches, never hand-set.
  - No-fabrication: a batch with no telemetry is EXCLUDED from pyrolysis
    stats, never defaulted into a fake peak of 0.
  - INV-1 tenancy: another org's batch never contributes to the caller's
    pyrolysis/permanence counts.

Reuses the batch-creation helpers from test_portal_metrics.py (same repo,
same module layout) rather than reinventing the corroborate/lab flow.
"""

import uuid as _uuid

import pytest

from tests.test_portal_metrics import (
    _create_batch,
    _corroborate,
    _lab,
    _login,
    _seed_projects,
)

pytestmark = pytest.mark.asyncio


async def test_pyrolysis_and_permanence_from_real_batches(
    client, registered_device, session_factory
):
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-quality@metrics.test", org_id="org-metrics-a"
    )

    # Fully issued batch: corroborated (telemetry) + labbed -> qualifies for
    # both pyrolysis and permanence metrics.
    bu = str(_uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu, project_id="dm-proj-a")
    await _lab(client, bu)

    resp = await client.get("/api/v1/portal/metrics/quality", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    pyro = body["pyrolysis"]
    assert pyro["n"] >= 1
    assert pyro["peak_temp_c"] is not None
    assert 600 <= pyro["peak_temp_c"]["avg"] <= 700
    assert pyro["pct_above_threshold"] is not None
    assert pyro["pct_above_threshold"]["avg"] > 90

    permanence = body["permanence"]
    assert permanence["n"] >= 1
    assert permanence["permanence_pct"] is not None
    assert 0 <= permanence["permanence_pct"]["avg"] <= 100
    assert len(permanence["distribution"]) == 4


async def test_batch_without_telemetry_is_excluded_not_defaulted(
    client, registered_device, session_factory
):
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-excl@metrics.test", org_id="org-metrics-a"
    )

    # Baseline: no batches yet for this fresh org user.
    baseline = await client.get("/api/v1/portal/metrics/quality", headers=headers)
    assert baseline.status_code == 200
    baseline_excluded = baseline.json()["pyrolysis"]["excluded"]

    # A batch created WITHOUT corroboration first -> no telemetry at all.
    bu = str(_uuid.uuid4())
    await _create_batch(client, bu, project_id="dm-proj-a")

    resp = await client.get("/api/v1/portal/metrics/quality", headers=headers)
    assert resp.status_code == 200, resp.text
    pyro = resp.json()["pyrolysis"]

    assert pyro["excluded"] >= baseline_excluded + 1
    # Never a fabricated zero peak leaking through as if it were real data.
    if pyro["n"] == 0:
        assert pyro["peak_temp_c"] is None
    else:
        # If other qualifying batches exist, the excluded one must not have
        # contributed a bogus zero.
        assert pyro["peak_temp_c"]["min"] > 0


async def test_org_isolation_quality_metrics(client, registered_device, session_factory):
    await _seed_projects(session_factory)

    # Org B: a fully issued, labbed, corroborated batch that must never
    # contribute to org A's counts.
    headers_b = await _login(
        client, session_factory, email="orgb-quality@metrics.test", org_id="org-metrics-b"
    )
    bu_b = str(_uuid.uuid4())
    await _corroborate(client, bu_b)
    await _create_batch(client, bu_b, project_id="dm-proj-b")
    await _lab(client, bu_b)

    # Org A: nothing at all.
    headers_a = await _login(
        client, session_factory, email="orga-iso@metrics.test", org_id="org-metrics-a"
    )

    resp_a = await client.get("/api/v1/portal/metrics/quality", headers=headers_a)
    assert resp_a.status_code == 200, resp_a.text
    body_a = resp_a.json()
    assert body_a["pyrolysis"]["n"] == 0
    assert body_a["pyrolysis"]["excluded"] == 0
    assert body_a["permanence"]["n"] == 0
    assert body_a["permanence"]["excluded"] == 0

    resp_b = await client.get("/api/v1/portal/metrics/quality", headers=headers_b)
    assert resp_b.status_code == 200, resp_b.text
    body_b = resp_b.json()
    assert body_b["pyrolysis"]["n"] >= 1
    assert body_b["permanence"]["n"] >= 1
