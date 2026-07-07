"""Rainbow T1.3 + T1.4: the C9 annual-methane and closed-kiln PAH gates.

These were dormant (never called) / hard-bypassed (enforced=False) before the
batch->project linkage (T1.1). Now a project-linked batch resolves its
(project_id, harvest-year) annual verification and gates on it; unlinked
(legacy) batches stay inert. The existing test_annual_verification_c9.py keeps
the legacy-inert assertions (its batches carry no project_id).
"""

import json
import uuid

import pytest
from sqlalchemy.future import select

from models import Batch

pytestmark = pytest.mark.asyncio

_ADMIN = {"X-Admin-Secret": "test-admin-secret"}
_SHA = "a" * 64
_HARVEST = "2026-07-03T00:00:00Z"  # -> production year 2026
_YEAR = 2026


async def _post_verif(client, project_id, **fields):
    body = {"project_id": project_id, "year": _YEAR}
    body.update(fields)
    return await client.post(
        "/api/v1/admin/annual-verification",
        content=json.dumps(body).encode("utf-8"),
        headers=_ADMIN,
    )


async def _telemetry(client, bu, kiln_type):
    await client.post(
        "/api/v1/telemetry",
        content=json.dumps(
            {
                "telemetry_uuid": str(uuid.uuid4()),
                "batch_uuid": bu,
                "kiln_type": kiln_type,
                "temperature_readings": [650.0] * 60,
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "tel-" + bu[:8]},
    )


async def _batch(client, bu, *, project_id=None):
    payload = {
        "batch_uuid": bu,
        "feedstock_species": "Lantana_camara",
        "harvest_timestamp": _HARVEST,
        "moisture_percent": 12.0,
        "harvest_uptime_seconds": 100,
    }
    if project_id is not None:
        payload["project_id"] = project_id
    await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode("utf-8"),
        headers={"X-Idempotency-Key": "b-" + bu[:8]},
    )


async def _reasons(session_factory, bu):
    async with session_factory() as s:
        b = (
            await s.execute(select(Batch).where(Batch.batch_uuid == uuid.UUID(bu)))
        ).scalar_one()
        return json.loads(b.provisional_reasons or "[]")


# ---- T1.3 annual methane -------------------------------------------------


async def test_methane_missing_when_no_verification(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _batch(client, bu, project_id="P-METH-1")
    assert "missing_annual_methane" in await _reasons(session_factory, bu)


async def test_methane_missing_when_too_few_runs(
    client, registered_device, session_factory
):
    await _post_verif(client, "P-METH-2", methane_run_count=2)
    bu = str(uuid.uuid4())
    await _batch(client, bu, project_id="P-METH-2")
    assert "missing_annual_methane" in await _reasons(session_factory, bu)


async def test_methane_ok_with_three_runs(
    client, registered_device, session_factory
):
    await _post_verif(client, "P-METH-3", methane_run_count=3)
    bu = str(uuid.uuid4())
    await _batch(client, bu, project_id="P-METH-3")
    assert "missing_annual_methane" not in await _reasons(session_factory, bu)


async def test_methane_wrong_year_gates(client, registered_device, session_factory):
    # Verification exists but for a different year than the batch's harvest year.
    await client.post(
        "/api/v1/admin/annual-verification",
        content=json.dumps(
            {"project_id": "P-METH-4", "year": 2025, "methane_run_count": 3}
        ).encode("utf-8"),
        headers=_ADMIN,
    )
    bu = str(uuid.uuid4())
    await _batch(client, bu, project_id="P-METH-4")
    assert "missing_annual_methane" in await _reasons(session_factory, bu)


async def test_methane_inert_without_project_linkage(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _batch(client, bu)  # no project_id
    assert "missing_annual_methane" not in await _reasons(session_factory, bu)


# ---- T1.4 closed-kiln PAH ------------------------------------------------


async def test_pah_missing_for_closed_kiln_without_measurement(
    client, registered_device, session_factory
):
    await _post_verif(client, "P-PAH-1", methane_run_count=3, pah_measured=False)
    bu = str(uuid.uuid4())
    await _telemetry(client, bu, "closed")
    await _batch(client, bu, project_id="P-PAH-1")
    assert "missing_pah" in await _reasons(session_factory, bu)


async def test_pah_missing_when_no_verification_row(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _telemetry(client, bu, "closed")
    await _batch(client, bu, project_id="P-PAH-2")
    assert "missing_pah" in await _reasons(session_factory, bu)


async def test_pah_ok_when_measured(client, registered_device, session_factory):
    await _post_verif(client, "P-PAH-3", methane_run_count=3, pah_measured=True)
    bu = str(uuid.uuid4())
    await _telemetry(client, bu, "closed")
    await _batch(client, bu, project_id="P-PAH-3")
    assert "missing_pah" not in await _reasons(session_factory, bu)


async def test_pah_inert_for_open_kiln(client, registered_device, session_factory):
    await _post_verif(client, "P-PAH-4", methane_run_count=3, pah_measured=False)
    bu = str(uuid.uuid4())
    await _telemetry(client, bu, "open")
    await _batch(client, bu, project_id="P-PAH-4")
    assert "missing_pah" not in await _reasons(session_factory, bu)


async def test_pah_inert_without_project_linkage(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    await _telemetry(client, bu, "closed")
    await _batch(client, bu)  # no project_id
    assert "missing_pah" not in await _reasons(session_factory, bu)


def test_no_enforced_false_bypass_in_server_source():
    """Regression: the hardcoded PAH bypass must never come back."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "server.py").read_text(
        encoding="utf-8"
    )
    assert "enforced=False" not in src
