"""Phase 8 — measured permanence or PROVISIONAL.

The H:Corg ratio is the permanence determinant for issuance. When no
lab-measured value is supplied the engine falls back to a conservative 0.35
assumption, but the resulting credit must be flagged PROVISIONAL and never
issued as final. `step3_cremain` no longer carries a silent default — the ratio
must be passed explicitly.
"""

import json
from uuid import uuid4

import pytest

from lca_engine import calculate_carbon_credit, sign_lca_audit, step3_cremain


# ---- engine-level ---------------------------------------------------------


def test_step3_requires_explicit_ratio():
    # Keyword-only with no default → omitting it is a programming error.
    with pytest.raises(TypeError):
        step3_cremain(0.1, 0.6)  # type: ignore[call-arg]
    # Passing None explicitly is rejected with a clear message.
    with pytest.raises(ValueError):
        step3_cremain(0.1, 0.6, h_corg_ratio=None)  # type: ignore[arg-type]


def test_no_lab_value_is_provisional():
    audit = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=12.0,
        min_recorded_temp_c=210.0,
        transport_distance_km=0.0,
    )
    assert audit.provisional is True


def test_lab_value_is_not_provisional():
    audit = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=12.0,
        min_recorded_temp_c=210.0,
        transport_distance_km=0.0,
        h_corg_ratio=0.3,
    )
    assert audit.provisional is False


def test_provisional_fallback_matches_explicit_035():
    # Provisional fallback must use exactly 0.35 — same number, just flagged.
    prov = calculate_carbon_credit(
        wet_yield_kg=100.0, moisture_percent=12.0, min_recorded_temp_c=210.0
    )
    explicit = calculate_carbon_credit(
        wet_yield_kg=100.0,
        moisture_percent=12.0,
        min_recorded_temp_c=210.0,
        h_corg_ratio=0.35,
    )
    assert prov.net_credit_t_co2e == explicit.net_credit_t_co2e
    assert prov.provisional is True and explicit.provisional is False


def test_audit_is_deterministic():
    a1 = calculate_carbon_credit(
        wet_yield_kg=115.4,
        moisture_percent=12.7,
        min_recorded_temp_c=210.0,
        transport_distance_km=14.2,
        h_corg_ratio=0.35,
    )
    a2 = calculate_carbon_credit(
        wet_yield_kg=115.4,
        moisture_percent=12.7,
        min_recorded_temp_c=210.0,
        transport_distance_km=14.2,
        h_corg_ratio=0.35,
    )

    def _canon(a):
        d = {k: v for k, v in a.__dict__.items() if k != "audit_signature"}
        return json.dumps(d, sort_keys=True)

    assert _canon(a1) == _canon(a2)
    # Same batch_uuid + same inputs → same signature (deterministic).
    bu = "11111111-1111-1111-1111-111111111111"
    assert sign_lca_audit(a1, "test-secret", batch_uuid=bu) == sign_lca_audit(
        a2, "test-secret", batch_uuid=bu
    )


def test_signature_is_bound_to_batch_uuid():
    # Phase 15-B: identical physical inputs but DIFFERENT batch_uuid → different
    # signature (no cross-batch replay of an issuance signature).
    kw = dict(
        wet_yield_kg=115.4,
        moisture_percent=12.7,
        min_recorded_temp_c=210.0,
        transport_distance_km=14.2,
        h_corg_ratio=0.35,
    )
    a1 = calculate_carbon_credit(**kw)
    a2 = calculate_carbon_credit(**kw)
    s1 = sign_lca_audit(
        a1, "test-secret", batch_uuid="aaaaaaaa-0000-0000-0000-000000000001"
    )
    s2 = sign_lca_audit(
        a2, "test-secret", batch_uuid="bbbbbbbb-0000-0000-0000-000000000002"
    )
    assert s1 != s2


# ---- API-level ------------------------------------------------------------


def _payload(**overrides) -> dict:
    p = {
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": "2026-01-01T00:00:00Z",
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
        "wet_yield_kg": 100.0,
        "min_recorded_temp_c": 0.0,  # 0 → no qualifying-telemetry requirement
        "transport_distance_km": 0.0,
    }
    p.update(overrides)
    return p


@pytest.mark.asyncio
async def test_batch_without_lab_hcorg_is_provisional(client):
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(_payload()).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid4()),
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["provisional"] is True


async def _corroborate(client, bu, lat=12.9716, lon=77.5946):
    """Post the telemetry/yield/application evidence that corroborates a batch's
    physical credit inputs (Phase 7-R). The conftest client auto-signs as the
    seeded test device."""
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid4()),
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
                "yield_uuid": str(uuid4()),
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
                "application_uuid": str(uuid4()),
                "batch_uuid": bu,
                "latitude": lat + 1.0,  # ~111 km from the batch → nonzero transport
                "longitude": lon,
                # C5 (enforced at C10): delivery record + buyer identity.
                "delivery_date": "2026-07-03T00:00:00Z",
                "delivered_amount_kg": 50.0,
                "buyer_name": "Asha Co-op",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "app-" + bu[:8]},
    )
    # Rainbow C2: supply the floor of 10 photographed moisture readings.
    for i in range(1, 11):
        await client.post(
            "/api/v1/moisture",
            content=json.dumps(
                {
                    "reading_uuid": str(uuid4()),
                    "batch_uuid": bu,
                    "moisture_percent": 12.0,
                    "sequence": i,
                    "sha256_hash": "a" * 64,
                }
            ).encode("utf-8"),
            headers={"X-Idempotency-Key": f"moist-{bu[:6]}-{i}"},
        )
    # C4 (enforced at C10): a photographed site composite pile sub-sample.
    await client.post(
        "/api/v1/composite-sample",
        content=json.dumps(
            {
                "sample_uuid": str(uuid4()),
                "batch_uuid": bu,
                "sha256_hash": "a" * 64,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "cs-" + bu[:8]},
    )


@pytest.mark.asyncio
async def test_batch_with_full_lab_is_not_provisional(client):
    # Phase 8-R + C7: not-provisional requires fully-corroborated physical inputs
    # AND both lab permanence inputs (H:Corg + organic Corg) via the authenticated
    # /admin/lab channel (NOT the device batch payload). H:Corg alone no longer
    # suffices — organic Corg was previously a species-constant assumption.
    bu = str(uuid4())
    lat, lon = 12.9716, 77.5946
    await _corroborate(client, bu, lat, lon)
    r = await client.post(
        "/api/v1/batches",
        content=json.dumps(
            _payload(
                batch_uuid=bu,
                latitude=lat,
                longitude=lon,
                # C1 (enforced at C10): biomass input amount + method.
                biomass_input_kg=500.0,
                biomass_measurement_method="direct_weigh",
            )
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid4()),
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["provisional"] is True  # assumed_h_corg + assumed_corg

    # H:Corg alone: still provisional (Corg assumed).
    lab1 = await client.post(
        "/api/v1/admin/lab-hcorg",
        content=json.dumps({"batch_uuid": bu, "lab_h_corg": 0.3}).encode("utf-8"),
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert lab1.status_code == 200, lab1.text
    assert lab1.json()["provisional"] is True

    # Full lab (H:Corg + Corg): now issuable.
    lab2 = await client.post(
        "/api/v1/admin/lab",
        content=json.dumps(
            {"batch_uuid": bu, "lab_h_corg": 0.3, "organic_carbon_pct": 0.60}
        ).encode("utf-8"),
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    assert lab2.status_code == 200, lab2.text
    assert lab2.json()["provisional"] is False
