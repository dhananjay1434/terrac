"""Phase 16-D — a repeat /metadata POST is a status UPDATE, not a no-op.

closeBatch flips sync_status -> CLOSED_PENDING_UPLOAD and enqueues the change;
the server must upsert the latest signed metadata so the close actually propagates
(previously the batch_uuid unique constraint made the second POST a silent no-op).
"""

import json
import uuid

import pytest
from sqlalchemy.future import select

from models import SystemMetadata

pytestmark = pytest.mark.asyncio


async def _post_meta(client, bu, sync_status):
    return await client.post(
        "/api/v1/metadata",
        content=json.dumps(
            {
                "batch_uuid": bu,
                "artisan_id": "art-1",
                "device_hardware_mac": "00:11:22",
                "app_build_version": "1.0",
                "sync_status": sync_status,
                "created_at": "2026-01-01T00:00:00Z",
            }
        ).encode("utf-8"),
        headers={"X-Idempotency-Key": "meta-" + bu[:8] + "-" + sync_status[:4]},
    )


async def test_metadata_repost_updates_sync_status(
    client, registered_device, session_factory
):
    bu = str(uuid.uuid4())
    r1 = await _post_meta(client, bu, "PENDING")
    assert r1.status_code == 201, r1.text

    r2 = await _post_meta(client, bu, "CLOSED_PENDING_UPLOAD")
    assert r2.status_code == 201, r2.text
    assert r2.json().get("updated") is True

    async with session_factory() as s:
        row = (
            await s.execute(
                select(SystemMetadata).where(SystemMetadata.batch_uuid == bu)
            )
        ).scalar_one()
    assert json.loads(row.payload_json)["sync_status"] == "CLOSED_PENDING_UPLOAD"
