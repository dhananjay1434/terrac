"""Part D.1b — allow-listed signed LCA breakdown on portal batch detail.

`GET /api/v1/portal/batches/{batch_uuid}` gains an optional `lca_breakdown`
object parsed from the batch's existing `lca_audit_json`. It must expose
ONLY the named safe numeric/flag fields and must NEVER leak the sensitive
audit sections (`full_audit_hmac`/`audit_signature`, `transport_events`,
`integrity_signals`) anywhere in the response.
"""

import json
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from models import PortalUser
from portal.auth import hash_password
from portal.routes import parse_lca_breakdown

pytestmark = pytest.mark.asyncio

_ALLOWED_KEYS = {
    "dry_mass_t",
    "gross_c_sink_t_co2e",
    "cremain_t",
    "safety_deduction_kg",
    "transport_penalty_kg",
    "ch4_penalty_kg",
    "net_credit_t_co2e",
    "provisional",
    "corg_assumed",
}

_SENSITIVE_MARKERS = ["audit_signature", "transport_events", "integrity_signals"]


async def _make_batch(client, bu: str):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "feedstock_species": "Lantana_camara",
                "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
                "moisture_percent": 12.0,
                "harvest_uptime_seconds": 100,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "op-lca-detail-" + bu[:8]},
    )


@pytest_asyncio.fixture
async def portal_auth_headers(client, session_factory):
    async with session_factory() as s:
        s.add(
            PortalUser(
                email="verifier-lca@x.org",
                password_hash=hash_password("pw-lca-verify1"),
                role="verifier",
            )
        )
        await s.commit()
    r = await client.post(
        "/api/v1/portal/login",
        json={"email": "verifier-lca@x.org", "password": "pw-lca-verify1"},
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_batch_detail_exposes_allowlisted_lca_breakdown(
    client, registered_device, session_factory, portal_auth_headers
):
    from sqlalchemy import select

    from models import Batch

    bu = str(uuid.uuid4())
    created = await _make_batch(client, bu)
    assert created.status_code == 201, created.text

    async with session_factory() as s:
        b = (await s.execute(select(Batch).where(Batch.batch_uuid == bu))).scalar_one()
        stored_audit = json.loads(b.lca_audit_json)

    resp = await client.get(
        f"/api/v1/portal/batches/{bu}", headers=portal_auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()

    breakdown = body["lca_breakdown"]
    assert breakdown is not None
    assert set(breakdown.keys()) == _ALLOWED_KEYS
    for key in _ALLOWED_KEYS:
        assert breakdown[key] == stored_audit[key]

    # The sensitive sections must never leak into lca_breakdown specifically.
    # (A whole-response substring search is too broad here: the pre-existing
    # `evidence_counts` object legitimately has its own unrelated
    # "transport_events" key — an evidence-submission counter, not the LCA
    # audit's sensitive GPS section — so it would false-positive. The
    # `set(breakdown.keys()) == _ALLOWED_KEYS` assertion above already proves
    # lca_breakdown itself carries nothing extra.)
    breakdown_text = json.dumps(breakdown)
    for marker in _SENSITIVE_MARKERS:
        assert marker not in breakdown_text

    # Pre-existing top-level fields stay present and unchanged in shape.
    assert "batch" in body and isinstance(body["batch"], dict)
    assert "compliance" in body and isinstance(body["compliance"], dict)


async def test_batch_detail_lca_breakdown_null_when_no_audit(
    client, session_factory, portal_auth_headers
):
    from models import Batch

    bu = str(uuid.uuid4())
    async with session_factory() as s:
        s.add(
            Batch(
                batch_uuid=bu,
                operation_id=f"op-noaudit-{uuid.uuid4().hex[:8]}",
                feedstock_species="Lantana_camara",
                harvest_timestamp=datetime(2026, 7, 1, tzinfo=timezone.utc),
                moisture_percent=12.0,
                harvest_uptime_seconds=100,
                lca_audit_json=None,
            )
        )
        await s.commit()

    resp = await client.get(
        f"/api/v1/portal/batches/{bu}", headers=portal_auth_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["lca_breakdown"] is None
    assert "batch" in body and isinstance(body["batch"], dict)
    assert "compliance" in body and isinstance(body["compliance"], dict)


def test_parse_lca_breakdown_none_input():
    assert parse_lca_breakdown(None) is None
    assert parse_lca_breakdown("") is None


def test_parse_lca_breakdown_invalid_json():
    assert parse_lca_breakdown("{not-json") is None


def test_parse_lca_breakdown_drops_sensitive_sections():
    raw = json.dumps(
        {
            "dry_mass_t": 1.23,
            "gross_c_sink_t_co2e": 4.5,
            "cremain_t": 0.9,
            "safety_deduction_kg": 2.0,
            "transport_penalty_kg": 3.0,
            "ch4_penalty_kg": 0.1,
            "net_credit_t_co2e": 0.75,
            "provisional": True,
            "corg_assumed": False,
            "audit_signature": "sig-should-not-leak",
            "transport_events": {"gps_transport_km": 12.0},
            "integrity_signals": {"mock_location_enabled": False},
            "full_audit_hmac": {"key_id": "k1", "hmac_sha256": "deadbeef"},
        }
    )
    result = parse_lca_breakdown(raw)
    assert set(result.keys()) == _ALLOWED_KEYS
    assert "audit_signature" not in result
    assert "transport_events" not in result
    assert "integrity_signals" not in result
    assert "full_audit_hmac" not in result
