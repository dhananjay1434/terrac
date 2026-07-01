"""
Client↔Server CONTRACT tests.

Everything else in this suite constructs *synthetic* payloads that happen to
match the server's models. These tests instead use the EXACT payload shapes the
real Flutter client emits (lifted verbatim from the Dart outbox writers) and
fire them at the real server with the global DB-execute mock disabled. They are
the missing gate: they verify the device can actually talk to the backend.

Golden sources (keep in sync with the Dart):
  * batch      → lib/data/local/app_database.dart  insertBiomassSourcingWithOutbox
  * telemetry  → lib/data/local/pyrolysis_writer.dart insertPyrolysisTelemetryWithOutbox

Tests currently expected to FAIL are marked xfail(strict=True) with the finding
they pin. When the contract is reconciled, the xfail flips to xpass and the
strict marker forces us to delete it — the spec is self-cleaning.
"""

from __future__ import annotations

import json
from uuid import uuid4
from datetime import datetime, timezone

import pytest


def golden_biomass_sourcing_payload() -> dict:
    """EXACT fields the device sends to /api/v1/batches (biomass_sourcing).

    Mirrors insertBiomassSourcingWithOutbox in app_database.dart. Note what is
    NOT here: wet_yield_kg, min_recorded_temp_c, transport_distance_km. The real
    client never sends them — they are meant to be corroborated server-side from
    the /telemetry, /yield and /application streams.
    """
    return {
        "sourcing_uuid": str(uuid4()),
        "batch_uuid": str(uuid4()),
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": datetime.now(timezone.utc).isoformat(),
        "moisture_percent": 14.5,
        "moisture_compliant": True,
        "photo_path": "/sandbox/evidence/harvest.jpg",
        "sha256_hash": "a" * 64,
        "latitude": 12.9716,
        "longitude": 77.5946,
        "mock_location_enabled": False,
        "harvest_uptime_seconds": 3600,
        "azimuth": 12.0,
        "pitch": 3.0,
        "roll": 1.0,
    }


@pytest.mark.asyncio
async def test_real_client_batch_payload_is_accepted(client, registered_device):
    """The exact payload a real device emits must be accepted by /batches."""
    payload = golden_biomass_sourcing_payload()
    resp = await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "contract-batch-1"},
    )
    assert resp.status_code in (200, 201), (
        f"real client batch payload rejected: {resp.status_code} {resp.text}"
    )


def test_telemetry_temperature_key_agreement():
    """The key the client writes must equal the key the server consumes.

    Pure source-contract check (no DB). The consumer is corroboration.derive_min_temp
    (Phase 7-R moved derivation out of create_batch). No server file may read the
    old camelCase 'temperatureReadingsJson' key anymore.
    """
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    writer = (repo / "lib/data/local/pyrolysis_writer.dart").read_text(encoding="utf-8")
    corr_src = (repo / "backend/corroboration.py").read_text(encoding="utf-8")
    server_src = (repo / "backend/server.py").read_text(encoding="utf-8")

    client_sends_snake = "'temperature_readings':" in writer
    consumer_reads_snake = '.get("temperature_readings"' in corr_src
    camel_anywhere = '"temperatureReadingsJson"' in (corr_src + server_src)

    assert client_sends_snake, "client no longer sends temperature_readings"
    assert consumer_reads_snake, "corroboration no longer reads temperature_readings"
    assert not camel_anywhere, (
        "a backend module still reads the camelCase temperatureReadingsJson key"
    )
