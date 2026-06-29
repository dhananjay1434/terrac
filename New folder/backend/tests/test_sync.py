"""End-to-end tests for POST /api/v1/batches/sync.

Runs against an in-memory SQLite via SQLAlchemy's aiosqlite driver — no
PostgreSQL needed for CI. Spins up a private engine + session factory and
overrides the FastAPI dependency.
"""
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path
from uuid import uuid4

import pytest
pytest.skip("Phase 5 SyncOutbox endpoint not yet implemented", allow_module_level=True)
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Make `import server` work regardless of where pytest is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import app, get_session  # noqa: E402
from models import Base  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def client():
    """Spin up a fresh in-memory SQLite per test + override dependency."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestSession = async_sessionmaker(test_engine, expire_on_commit=False)

    async def _create():
        async with test_engine.begin() as c:
            await c.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_create())

    async def _override_session():
        async with TestSession() as s:
            yield s

    app.dependency_overrides[get_session] = _override_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture()
def sample_payload():
    batch_uuid = str(uuid4())
    return {
        "system_metadata": {
            "batch_uuid": batch_uuid,
            "artisan_id": "artisan-001",
            "device_hardware_mac": "AA:BB:CC:DD:EE:FF",
            "app_build_version": "1.0.0+1",
            "sync_status": "PENDING",
            "created_at": "2026-01-15T08:00:00Z",
        },
        "biomass_sourcing": {
            "sourcing_uuid": str(uuid4()),
            "batch_uuid": batch_uuid,
            "feedstock_species": "Lantana_camara",
            "harvest_timestamp": "2026-01-12T08:00:00Z",
            "moisture_percent": 12.5,
            "moisture_compliant": True,
            "photo_path": "/sandbox/evidence/abc.jpg",
            "sha256_hash": _sha256("evidence-1"),
            "latitude": 12.9716,
            "longitude": 77.5946,
            "mock_location_enabled": False,
        },
        "pyrolysis_telemetry": {
            "telemetry_uuid": str(uuid4()),
            "batch_uuid": batch_uuid,
            "kiln_gross_capacity": 200.0,
            "burn_start_timestamp": "2026-01-15T09:00:00Z",
            "burn_end_timestamp": "2026-01-15T13:00:00Z",
            "min_temp": 480.0,
            "max_temp": 612.5,
            "temperature_readings": [
                480.0, 500.0, 540.0, 580.0, 612.5, 600.0, 595.0, 575.0
            ],
        },
        "yield_metrics": {
            "yield_uuid": str(uuid4()),
            "batch_uuid": batch_uuid,
            "quench_methodology": "WATER_QUENCH",
            "gross_volume": 200.0,
            "wet_yield_weight_kg": 42.350,
            "dry_yield_weight_kg": None,
        },
        "end_use_application": {
            "application_uuid": str(uuid4()),
            "batch_uuid": batch_uuid,
            "application_methodology": "ROOT_ZONE_TRENCHING",
            "application_rate_tonnes": 0.42,
            "transport_distance_km": 0.0,
            "latitude": 12.9720,
            "longitude": 77.5950,
            "farmer_photo_path": "/sandbox/evidence/farmer.jpg",
            "farmer_photo_sha256": _sha256("farmer-1"),
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sync_first_insert_returns_200_and_stores(client, sample_payload):
    key = "idem-" + uuid4().hex
    r = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": key},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["batch_uuid"] == sample_payload["system_metadata"]["batch_uuid"]
    assert body["idempotency_key"] == key
    assert body["sync_status"] == "RECEIVED"
    assert body["duplicate"] is False


def test_sync_duplicate_same_key_returns_200_no_duplicate_row(
    client, sample_payload
):
    key = "idem-" + uuid4().hex
    r1 = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": key},
    )
    assert r1.status_code == 200
    assert r1.json()["duplicate"] is False

    # Submit the exact same payload + key. Must NOT raise the UNIQUE
    # constraint — the endpoint must short-circuit to the duplicate path.
    r2 = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": key},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["duplicate"] is True
    assert body2["batch_uuid"] == r1.json()["batch_uuid"]
    assert body2["idempotency_key"] == key
    # received_at must point at the ORIGINAL row (not a fresh insert).
    # We compare the prefix to be SQLite-tz-format tolerant.
    assert body2["received_at"][:19] == r1.json()["received_at"][:19]


def test_missing_idempotency_header_returns_422(client, sample_payload):
    # FastAPI's Header(...) makes the header required → 422 Unprocessable.
    r = client.post("/api/v1/batches/sync", json=sample_payload)
    assert r.status_code == 422


def test_schema_drift_extra_field_returns_422(client, sample_payload):
    sample_payload["system_metadata"]["nope"] = "extra-field"
    r = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": "idem-" + uuid4().hex},
    )
    assert r.status_code == 422


def test_invalid_method_enum_returns_422(client, sample_payload):
    sample_payload["end_use_application"]["application_methodology"] = "SKY_BURN"
    r = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": "idem-" + uuid4().hex},
    )
    assert r.status_code == 422


def test_batch_uuid_mismatch_returns_422(client, sample_payload):
    sample_payload["biomass_sourcing"]["batch_uuid"] = str(uuid4())
    r = client.post(
        "/api/v1/batches/sync",
        json=sample_payload,
        headers={"X-Idempotency-Key": "idem-" + uuid4().hex},
    )
    assert r.status_code == 422
