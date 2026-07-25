"""HTTP endpoint tests for portal routes — Phase 2 bucket parameter exposure.

Tests the /api/v1/portal/metrics/credit-timeseries endpoint with bucket
parameter validation and passing through to the backend function.
"""

import json
import uuid as _uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from models import AnnualVerification, Batch, BulkDensityTest, PortalUser, Project
from portal.auth import hash_password

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}  # matches conftest env shim


def _batch_payload(bu, project_id=None, lat=12.9716, lon=77.5946):
    return {
        "sourcing_uuid": str(_uuid.uuid4()),
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "moisture_compliant": True,
        "photo_path": "/x.jpg",
        "sha256_hash": "a" * 64,
        "latitude": lat,
        "longitude": lon,
        "harvest_uptime_seconds": 3600,
        "biomass_input_kg": 500.0,
        "biomass_measurement_method": "direct_weigh",
        "project_id": project_id,
    }


async def _corroborate(client, bu, lat=12.9716, lon=77.5946):
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(_uuid.uuid4()),
                "batch_uuid": bu,
                "temperature_readings": [650.0] * 60,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "tel-" + bu[:8]},
    )
    await client.post(
        "/api/v1/yield",
        content=json.dumps(
            {
                "yield_uuid": str(_uuid.uuid4()),
                "batch_uuid": bu,
                "wet_yield_weight_kg": 100.0,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "yld-" + bu[:8]},
    )
    await client.post(
        "/api/v1/application",
        content=json.dumps(
            {
                "application_uuid": str(_uuid.uuid4()),
                "batch_uuid": bu,
                "latitude": lat + 1.0,
                "longitude": lon,
                "delivery_date": "2026-07-03T00:00:00Z",
                "delivered_amount_kg": 50.0,
                "buyer_name": "Asha Co-op",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "app-" + bu[:8]},
    )
    await client.post(
        "/api/v1/composite-sample",
        content=json.dumps(
            {
                "sample_uuid": str(_uuid.uuid4()),
                "batch_uuid": bu,
                "sha256_hash": "a" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "cs-" + bu[:8]},
    )
    for i in range(1, 11):
        await client.post(
            "/api/v1/moisture",
            content=json.dumps(
                {
                    "reading_uuid": str(_uuid.uuid4()),
                    "batch_uuid": bu,
                    "moisture_percent": 12.0,
                    "sequence": i,
                    "sha256_hash": "a" * 64,
                }
            ).encode("utf-8"),
            headers={"X-Idempotency-Key": f"moist-{bu[:6]}-{i}"},
        )


async def _create_batch(client, bu, project_id=None):
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(_batch_payload(bu, project_id=project_id)).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )
    assert r.status_code == 201, r.text
    return r


async def _lab(client, bu):
    r = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.60}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    assert r.status_code == 200, r.text
    return r


async def _make_issued_batch(client, session_factory, project_id, received_at):
    """Full corroboration + lab call -> provisional=False, real non-zero credit."""
    bu = str(_uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu, project_id=project_id)
    await _lab(client, bu)
    return await _set_received_at(session_factory, bu, received_at)


async def _set_received_at(session_factory, bu, received_at):
    async with session_factory() as s:
        row = (
            await s.execute(select(Batch).where(Batch.batch_uuid == str(_uuid.UUID(bu))))
        ).scalar_one()
        row.received_at = received_at
        await s.commit()
        await s.refresh(row)
        return row


async def _seed_projects(session_factory):
    """Seed projects and compliance requirements for bucketing tests."""
    year = datetime.now(timezone.utc).year
    future = datetime.now(timezone.utc) + timedelta(days=365)
    async with session_factory() as session:
        session.add_all(
            [
                Project(project_id="routes-proj-a", name="Routes Test Org A", org_id="org-routes-a"),
                AnnualVerification(
                    project_id="routes-proj-a", year=year, methane_run_count=3, payload_json="{}"
                ),
                BulkDensityTest(
                    test_uuid=str(_uuid.uuid4()),
                    project_id="routes-proj-a",
                    density_kg_per_l=0.3,
                    valid_until=future,
                ),
            ]
        )
        await session.commit()


async def _login(client, session_factory, *, email, org_id):
    async with session_factory() as session:
        session.add(
            PortalUser(
                email=email,
                password_hash=hash_password("correct-horse-battery-staple"),
                role="org_admin",
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


WINDOW_FROM = "2026-07-01T00:00:00+00:00"
WINDOW_TO = "2026-07-31T23:59:59+00:00"


async def test_get_credit_timeseries_bucket_day_param(
    client, registered_device, session_factory
):
    """Phase 2: HTTP GET with bucket=day parameter.

    Scenario: Make an HTTP GET request to /portal/credit-timeseries?bucket=day
    - Response status 200
    - Response bucket field = "day"
    - Period format in response is YYYY-MM-DD
    """
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="routes-day@test", org_id="org-routes-a"
    )

    # Create a batch on July 15
    batch_jul15 = await _make_issued_batch(
        client,
        session_factory,
        "routes-proj-a",
        datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert batch_jul15.net_credit_t_co2e != 0.0

    # Request with bucket=day
    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"bucket": "day", "from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Assert bucket field is "day"
    assert body["bucket"] == "day"

    # Assert response has buckets with YYYY-MM-DD format
    assert len(body["buckets"]) > 0
    for bucket_item in body["buckets"]:
        period = bucket_item["period"]
        # Verify YYYY-MM-DD format (10 chars, dashes at positions 4 and 7)
        assert len(period) == 10, f"Expected format YYYY-MM-DD, got {period}"
        assert period[4] == "-" and period[7] == "-"

    # Verify the batch's day has non-zero credit
    by_period = {b["period"]: b for b in body["buckets"]}
    day15 = by_period.get("2026-07-15")
    assert day15 is not None
    assert day15["issued_credit_t_co2e"] == pytest.approx(batch_jul15.net_credit_t_co2e)
    assert day15["issued_count"] == 1


async def test_get_credit_timeseries_invalid_bucket_returns_422(
    client, registered_device, session_factory
):
    """Phase 2: HTTP GET with invalid bucket value returns 422 (validation error).

    Scenario: GET ?bucket=invalid should return 422 (FastAPI validation)
    """
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="routes-invalid@test", org_id="org-routes-a"
    )

    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"bucket": "invalid", "from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    # FastAPI's regex validation returns 422 for invalid input
    assert resp.status_code == 422


async def test_get_credit_timeseries_backward_compatibility_default_month(
    client, registered_device, session_factory
):
    """Phase 2: Backward compatibility — default to bucket=month without param.

    Scenario: GET without bucket param should default to "month"
    - Response status 200
    - Response bucket field = "month"
    - Period format is YYYY-MM (not YYYY-MM-DD)
    """
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="routes-compat@test", org_id="org-routes-a"
    )

    # Create a batch in July
    batch_jul = await _make_issued_batch(
        client,
        session_factory,
        "routes-proj-a",
        datetime(2026, 7, 15, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert batch_jul.net_credit_t_co2e != 0.0

    # Request WITHOUT bucket parameter
    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    # Assert bucket defaults to "month"
    assert body["bucket"] == "month"

    # Assert period format is YYYY-MM (7 chars)
    assert len(body["buckets"]) > 0
    for bucket_item in body["buckets"]:
        period = bucket_item["period"]
        # Verify YYYY-MM format (7 chars, dash at position 4)
        assert len(period) == 7, f"Expected format YYYY-MM, got {period}"
        assert period[4] == "-"

    # July bucket should have the batch's credit
    by_period = {b["period"]: b for b in body["buckets"]}
    july = by_period.get("2026-07")
    assert july is not None
    assert july["issued_credit_t_co2e"] == pytest.approx(batch_jul.net_credit_t_co2e)
    assert july["issued_count"] == 1
