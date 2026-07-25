"""V8 Part D.1a — GET /api/v1/portal/metrics/credit-timeseries.

Org-scoped, SQL-aggregated (real GROUP BY, never Python bucketing) monthly
credit time-series. Covers:
  - INV-2: per-month sums match the real compute path (POST /api/v1/batches
    + full corroboration + /api/v1/admin/lab), never a hand-set credit.
  - INV-3: issued (provisional=false) and provisional ("pipeline") credit are
    reported separately; provisional never leaks into issued.
  - INV-5: a month inside the window with zero batches renders as a real
    zero bucket, never omitted.
  - INV-1: tenancy — another org's credit never appears for the caller's org.
  - bucket=week (or any non-"month" value) and windows over 60 months -> 400.

Uses the real device-signed batch flow (conftest's `client`/`registered_device`
fixtures + the corroborate/lab helpers mirrored from
tests/test_lab_hcorg_channel.py) so every credit figure asserted here is a
genuine LCA compute output, never fabricated. `received_at` is adjusted
directly on the row after creation (metadata only, not the credit) so batches
can be placed in specific UTC months deterministically.
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
    """Full corroboration + lab call -> provisional=False, real non-zero
    credit. Returns the reloaded row (with received_at overridden — metadata
    only, never the computed credit)."""
    bu = str(_uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu, project_id=project_id)
    await _lab(client, bu)
    return await _set_received_at(session_factory, bu, received_at)


async def _make_provisional_batch(client, session_factory, project_id, received_at):
    """Corroborated (non-zero credit input) but no lab call -> stays
    provisional (assumed H:Corg + assumed Corg)."""
    bu = str(_uuid.uuid4())
    await _corroborate(client, bu)
    await _create_batch(client, bu, project_id=project_id)
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
    # Batches here are project-linked (required for org scoping via
    # tenancy.scope_batches_by_org), which activates two project-scoped C10
    # gates that a legacy/no-project batch never hits: the annual methane
    # verification (>=3 runs) and the in-date bulk-density calibration. Both
    # must be satisfied here or every batch stays provisional=True regardless
    # of the lab call, which would silently zero out every "issued" figure
    # this test asserts.
    year = datetime.now(timezone.utc).year
    future = datetime.now(timezone.utc) + timedelta(days=365)
    async with session_factory() as session:
        session.add_all(
            [
                Project(project_id="dm-proj-a", name="Metrics Org A", org_id="org-metrics-a"),
                Project(project_id="dm-proj-b", name="Metrics Org B", org_id="org-metrics-b"),
                AnnualVerification(
                    project_id="dm-proj-a", year=year, methane_run_count=3, payload_json="{}"
                ),
                AnnualVerification(
                    project_id="dm-proj-b", year=year, methane_run_count=3, payload_json="{}"
                ),
                BulkDensityTest(
                    test_uuid=str(_uuid.uuid4()),
                    project_id="dm-proj-a",
                    density_kg_per_l=0.3,
                    valid_until=future,
                ),
                BulkDensityTest(
                    test_uuid=str(_uuid.uuid4()),
                    project_id="dm-proj-b",
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


MAY = datetime(2026, 5, 10, 8, 0, 0, tzinfo=timezone.utc)
JULY = datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc)
WINDOW_FROM = "2026-05-01T00:00:00+00:00"
WINDOW_TO = "2026-07-31T23:59:59+00:00"


async def test_timeseries_buckets_zero_fill_and_org_isolation(
    client, registered_device, session_factory
):
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga@metrics.test", org_id="org-metrics-a"
    )

    # Org A: one issued + one provisional batch in May, one issued in July.
    issued_may = await _make_issued_batch(client, session_factory, "dm-proj-a", MAY)
    prov_may = await _make_provisional_batch(client, session_factory, "dm-proj-a", MAY)
    issued_july = await _make_issued_batch(client, session_factory, "dm-proj-a", JULY)

    # Org B: an issued batch in July that must NEVER appear for the org-A caller.
    issued_july_org_b = await _make_issued_batch(
        client, session_factory, "dm-proj-b", JULY
    )

    assert issued_may.net_credit_t_co2e != 0.0
    assert prov_may.net_credit_t_co2e != 0.0
    assert issued_july.net_credit_t_co2e != 0.0
    assert issued_july_org_b.net_credit_t_co2e != 0.0

    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"bucket": "month", "from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    by_period = {b["period"]: b for b in body["buckets"]}
    assert set(by_period) == {"2026-05", "2026-06", "2026-07"}

    # May: only the issued batch counts toward issued_credit; provisional
    # is excluded (INV-3) and tallied separately.
    may = by_period["2026-05"]
    assert may["issued_credit_t_co2e"] == pytest.approx(issued_may.net_credit_t_co2e)
    assert may["issued_count"] == 1
    assert may["provisional_count"] == 1

    # June: genuinely zero, still present (INV-5).
    june = by_period["2026-06"]
    assert june["issued_credit_t_co2e"] == 0.0
    assert june["issued_count"] == 0
    assert june["provisional_count"] == 0

    # July: only org A's issued batch — org B's credit must never appear.
    july = by_period["2026-07"]
    assert july["issued_credit_t_co2e"] == pytest.approx(issued_july.net_credit_t_co2e)
    assert july["issued_count"] == 1
    org_b_credit = issued_july_org_b.net_credit_t_co2e
    assert july["issued_credit_t_co2e"] != pytest.approx(
        issued_july.net_credit_t_co2e + org_b_credit
    )

    totals = body["totals"]
    assert totals["issued_credit_t_co2e"] == pytest.approx(
        issued_may.net_credit_t_co2e + issued_july.net_credit_t_co2e
    )
    assert totals["issued_count"] == 2
    assert totals["provisional_count"] == 1
    assert totals["provisional_credit_t_co2e"] == pytest.approx(
        prov_may.net_credit_t_co2e
    )
    # Org B's credit is absent from the totals entirely (INV-1).
    assert totals["issued_credit_t_co2e"] != pytest.approx(
        issued_may.net_credit_t_co2e + issued_july.net_credit_t_co2e + org_b_credit
    )


async def test_unsupported_bucket_is_422(client, registered_device, session_factory):
    """FastAPI's pattern validation returns 422 for invalid bucket values."""
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-week@metrics.test", org_id="org-metrics-a"
    )
    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"bucket": "week", "from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    # FastAPI's pattern validation returns 422 (Unprocessable Entity), not 400
    assert resp.status_code == 422


async def test_window_over_60_months_is_400(client, registered_device, session_factory):
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-window@metrics.test", org_id="org-metrics-a"
    )
    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={
            "bucket": "month",
            "from": "2015-01-01T00:00:00+00:00",
            "to": "2026-01-01T00:00:00+00:00",
        },
        headers=headers,
    )
    assert resp.status_code == 400
    assert resp.json()["detail"] == "window_too_large"


async def test_bucket_components_reconcile_and_exclude_provisional(
    client, registered_device, session_factory
):
    """Part 1E.1: each bucket gains a `components` breakdown (safety/
    transport/ch4/gross, all tCO2e) summed over the SAME issued-only set as
    issued_credit_t_co2e.

    INV-4: gross - (safety + transport + ch4) reconciles to issued_credit
    within a loose tolerance (catches unit/sign blunders, not float noise).
    INV-3: a provisional batch's audit values must NOT leak into components —
    the bucket's components must reflect only the issued batch's contribution.
    """
    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-components@metrics.test", org_id="org-metrics-a"
    )

    issued_may = await _make_issued_batch(client, session_factory, "dm-proj-a", MAY)
    prov_may = await _make_provisional_batch(client, session_factory, "dm-proj-a", MAY)

    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"bucket": "month", "from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    by_period = {b["period"]: b for b in body["buckets"]}

    may = by_period["2026-05"]
    comp = may["components"]
    for key in ("safety_t_co2e", "transport_t_co2e", "ch4_t_co2e", "gross_t_co2e"):
        assert key in comp
        assert comp[key] is not None

    # INV-4: unit reconciliation against the SAME issued_credit_t_co2e.
    assert abs(
        comp["gross_t_co2e"]
        - (comp["safety_t_co2e"] + comp["transport_t_co2e"] + comp["ch4_t_co2e"])
        - may["issued_credit_t_co2e"]
    ) < 0.05

    # INV-3: components reflect ONLY the issued batch, never the provisional
    # one — confirmed by the same reconciliation holding against the single
    # issued batch's own net_credit_t_co2e (would fail if prov leaked in,
    # since prov_may.net_credit_t_co2e != 0.0).
    assert prov_may.net_credit_t_co2e != 0.0
    assert comp["gross_t_co2e"] - (
        comp["safety_t_co2e"] + comp["transport_t_co2e"] + comp["ch4_t_co2e"]
    ) == pytest.approx(issued_may.net_credit_t_co2e, abs=0.05)

    # A month with zero qualifying batches still gets all-zero components
    # (INV-5, consistent with the existing zero-fill).
    june = by_period["2026-06"]
    assert june["components"] == {
        "safety_t_co2e": 0.0,
        "transport_t_co2e": 0.0,
        "ch4_t_co2e": 0.0,
        "gross_t_co2e": 0.0,
    }


async def test_credit_timeseries_daily_bucketing(
    client, registered_device, session_factory
):
    """Daily bucketing support: bucket=day generates one row per calendar day,
    with zero-fill for days without batches (equivalent to INV-5 for days).

    Scenario: 3 batches spread across 14 days (day 1, day 7, day 14).
    - Result must have exactly 14 rows (one per calendar day).
    - Days with batches have non-zero issued credit.
    - Days without batches have zero issued credit (zero-fill must work).
    - Period format must be "YYYY-MM-DD" (not "YYYY-MM").

    Note: Tests the credit_timeseries() function directly (not through HTTP API)
    because API route validation is Phase 2. Phase 1 is backend function only.
    """
    from portal import metrics

    await _seed_projects(session_factory)

    # Create a user for the function call
    async with session_factory() as session:
        user = PortalUser(
            email="orga-daily-func@metrics.test",
            password_hash=hash_password("correct-horse-battery-staple"),
            role="org_admin",
            org_id="org-metrics-a",
            disabled=False,
        )
        session.add(user)
        await session.commit()

    # Define a 14-day window: July 1-14, 2026
    window_from = datetime(2026, 7, 1, 0, 0, 0, tzinfo=timezone.utc)
    window_to = datetime(2026, 7, 14, 23, 59, 59, tzinfo=timezone.utc)

    # Create 3 batches on days 1, 7, and 14 via HTTP (corroborate + lab)
    batch_day1 = await _make_issued_batch(
        client, session_factory, "dm-proj-a", datetime(2026, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    batch_day7 = await _make_issued_batch(
        client, session_factory, "dm-proj-a", datetime(2026, 7, 7, 12, 0, 0, tzinfo=timezone.utc)
    )
    batch_day14 = await _make_issued_batch(
        client, session_factory, "dm-proj-a", datetime(2026, 7, 14, 12, 0, 0, tzinfo=timezone.utc)
    )

    # Verify all batches have non-zero credit
    assert batch_day1.net_credit_t_co2e != 0.0
    assert batch_day7.net_credit_t_co2e != 0.0
    assert batch_day14.net_credit_t_co2e != 0.0

    # Call the metrics function directly with bucket="day"
    async with session_factory() as session:
        body = await metrics.credit_timeseries(
            session, user, window_from, window_to, bucket="day"
        )

    # Verify bucket type in response
    assert body["bucket"] == "day"

    # Verify exactly 14 rows (one per calendar day)
    assert len(body["buckets"]) == 14

    # Map by period (YYYY-MM-DD format)
    by_period = {b["period"]: b for b in body["buckets"]}

    # Verify period format is YYYY-MM-DD
    for period in by_period:
        # Check format: should be exactly 10 chars "YYYY-MM-DD"
        assert len(period) == 10
        assert period[4] == "-" and period[7] == "-"

    # Day 1 should have non-zero issued credit from batch_day1
    day1 = by_period["2026-07-01"]
    assert day1["issued_credit_t_co2e"] == pytest.approx(batch_day1.net_credit_t_co2e)
    assert day1["issued_count"] == 1
    assert day1["provisional_count"] == 0

    # Days 2-6 should have zero issued credit (zero-fill)
    for day_num in range(2, 7):
        day_key = f"2026-07-{day_num:02d}"
        day = by_period[day_key]
        assert day["issued_credit_t_co2e"] == 0.0
        assert day["issued_count"] == 0
        assert day["provisional_count"] == 0

    # Day 7 should have non-zero issued credit from batch_day7
    day7 = by_period["2026-07-07"]
    assert day7["issued_credit_t_co2e"] == pytest.approx(batch_day7.net_credit_t_co2e)
    assert day7["issued_count"] == 1
    assert day7["provisional_count"] == 0

    # Days 8-13 should have zero issued credit (zero-fill)
    for day_num in range(8, 14):
        day_key = f"2026-07-{day_num:02d}"
        day = by_period[day_key]
        assert day["issued_credit_t_co2e"] == 0.0
        assert day["issued_count"] == 0
        assert day["provisional_count"] == 0

    # Day 14 should have non-zero issued credit from batch_day14
    day14 = by_period["2026-07-14"]
    assert day14["issued_credit_t_co2e"] == pytest.approx(batch_day14.net_credit_t_co2e)
    assert day14["issued_count"] == 1
    assert day14["provisional_count"] == 0

    # Verify totals are correct
    totals = body["totals"]
    assert totals["issued_credit_t_co2e"] == pytest.approx(
        batch_day1.net_credit_t_co2e + batch_day7.net_credit_t_co2e + batch_day14.net_credit_t_co2e
    )
    assert totals["issued_count"] == 3
    assert totals["provisional_count"] == 0


async def test_credit_timeseries_backward_compatibility(
    client, registered_device, session_factory
):
    """Verify that calling credit_timeseries without the bucket parameter
    defaults to "month" bucketing and returns correct month granularity.

    Also verifies the HTTP API endpoint continues to work with default bucket=month
    (backward compatibility at the route level).
    """
    from portal import metrics

    await _seed_projects(session_factory)
    headers = await _login(
        client, session_factory, email="orga-compat@metrics.test", org_id="org-metrics-a"
    )

    # Create a user for the function call
    async with session_factory() as session:
        user = PortalUser(
            email="orga-compat-func@metrics.test",
            password_hash=hash_password("correct-horse-battery-staple"),
            role="org_admin",
            org_id="org-metrics-a",
            disabled=False,
        )
        session.add(user)
        await session.commit()

    # Create one batch in May
    issued_may = await _make_issued_batch(
        client, session_factory, "dm-proj-a", MAY
    )

    # Test 1: Call function directly WITHOUT bucket parameter (should default to "month")
    async with session_factory() as session:
        body = await metrics.credit_timeseries(
            session, user,
            datetime.fromisoformat(WINDOW_FROM.replace("+00:00", "+0:0").replace("+0:0", "").replace("Z", "") + "+00:00"),
            datetime.fromisoformat(WINDOW_TO.replace("+00:00", "+0:0").replace("+0:0", "").replace("Z", "") + "+00:00"),
            # Note: NOT passing bucket parameter, so default "month" should apply
        )

    # Verify bucket defaults to "month"
    assert body["bucket"] == "month"

    # Should return 3 rows (May, June, July)
    assert len(body["buckets"]) == 3
    by_period = {b["period"]: b for b in body["buckets"]}

    # Period format should be YYYY-MM
    for period in by_period:
        assert len(period) == 7  # "YYYY-MM" is 7 chars
        assert period[4] == "-"

    # May should have the issued batch's credit
    may = by_period["2026-05"]
    assert may["issued_credit_t_co2e"] == pytest.approx(issued_may.net_credit_t_co2e)
    assert may["issued_count"] == 1

    # June should be zero-filled
    june = by_period["2026-06"]
    assert june["issued_credit_t_co2e"] == 0.0
    assert june["issued_count"] == 0

    # July should be zero-filled (no batches)
    july = by_period["2026-07"]
    assert july["issued_credit_t_co2e"] == 0.0
    assert july["issued_count"] == 0

    # Test 2: Verify HTTP API endpoint also works with default bucket=month
    resp = await client.get(
        "/api/v1/portal/metrics/credit-timeseries",
        params={"from": WINDOW_FROM, "to": WINDOW_TO},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    api_body = resp.json()

    # HTTP API should also return month bucket
    assert api_body["bucket"] == "month"
    assert len(api_body["buckets"]) == 3
