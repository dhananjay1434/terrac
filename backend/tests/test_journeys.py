import pytest
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from models import Dispatch, DispatchSite, DispatchJourney, Batch
from schemas import DispatchJourneyCreate, DispatchManifestLineInput
from lca_engine import calculate_carbon_credit, LcaParams

@pytest.mark.asyncio
async def test_journey_endpoint(
    client: AsyncClient,
    session_factory,
    registered_device,
):
    # Setup dispatch
    async with session_factory() as session:
        dispatch = Dispatch(dispatch_uuid="11111111-1111-1111-1111-111111111111", kind="biochar", status="draft", device_id=registered_device["device_id"])
        session.add(dispatch)
        await session.commit()

    payload = {
        "device_id": registered_device["device_id"],
        "distance_source": "gps",
        "distance_km": 150.0,
        "fuel_type": "diesel",
        "vehicle_class": "diesel_truck_5t",
        "manifest": [{"product": "biochar", "count": 10}]
    }

    from tests.conftest import _ed25519_sign
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload["producer_signature"] = _ed25519_sign(canonical)

    resp = await client.post(
        f"/api/v2/dispatch/{dispatch.dispatch_uuid}/journey",
        json=payload,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "success"
    assert "emissions_kg" in data
    assert "factor_version" in data


def test_lca_conservativeness():
    # Base calculation with transport_distance_km = 150 (penalty applied)
    lca_base = calculate_carbon_credit(
        wet_yield_kg=1000,
        moisture_percent=10,
        min_recorded_temp_c=400,
        transport_distance_km=150, # > 100km threshold
    )
    
    base_penalty = lca_base.transport_penalty_kg
    assert base_penalty > 0

    # manual journey with tiny distance -> deduction unchanged (max(measured, default))
    lca_manual_tiny = calculate_carbon_credit(
        wet_yield_kg=1000,
        moisture_percent=10,
        min_recorded_temp_c=400,
        transport_distance_km=150,
        measured_transport_kg=1.0,  # tiny
        distance_source="manual"
    )
    assert lca_manual_tiny.transport_penalty_kg == base_penalty
    
    # manual journey with large distance -> deduction increased
    lca_manual_large = calculate_carbon_credit(
        wet_yield_kg=1000,
        moisture_percent=10,
        min_recorded_temp_c=400,
        transport_distance_km=150,
        measured_transport_kg=5000.0,  # large
        distance_source="manual"
    )
    assert lca_manual_large.transport_penalty_kg == 5000.0

    # gps journey with tiny distance -> deduction reduced
    lca_gps_tiny = calculate_carbon_credit(
        wet_yield_kg=1000,
        moisture_percent=10,
        min_recorded_temp_c=400,
        transport_distance_km=150,
        measured_transport_kg=1.0,  # tiny
        distance_source="gps"
    )
    assert lca_gps_tiny.transport_penalty_kg == 1.0
