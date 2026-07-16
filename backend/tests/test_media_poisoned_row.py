"""Audit fix 3: a media upload rejected for ownership (403) must leave NO
media_files row behind — otherwise a later legitimate retry hits the duplicate
fast-path and reports stored=True for bytes that were deleted."""

import hashlib
import io
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from models import Batch, MediaFile
from tests.remediation.crypto_utils import sign_media

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"  # seeded + enrolled by conftest
_JPEG = b"\xff\xd8\xff\xe0" + b"x" * 64  # minimal fake JPEG bytes


async def _seed_foreign_batch(session_factory, bu):
    """A batch owned by a DIFFERENT device than the uploading one."""
    async with session_factory() as s:
        s.add(
            Batch(
                batch_uuid=bu,
                operation_id="op-foreign-" + bu[:8],
                feedstock_species="Lantana_camara",
                harvest_timestamp=datetime.now(timezone.utc),
                moisture_percent=12.0,
                harvest_uptime_seconds=0,
                device_id="someone-elses-device",
                status="RECEIVED",
            )
        )
        await s.commit()


async def test_403_upload_leaves_no_row(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    await _seed_foreign_batch(session_factory, bu)
    sha = hashlib.sha256(_JPEG).hexdigest()
    op = "op-media-poison-" + bu[:8]

    def _headers():
        return {
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        }

    r = await client.post(
        "/api/v1/media",
        files={"file": ("p.jpg", io.BytesIO(_JPEG), "image/jpeg")},
        headers=_headers(),
    )
    assert r.status_code == 403, r.text

    # THE core assertion: no stranded media_files row under that op-id.
    async with session_factory() as s:
        row = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one_or_none()
    assert row is None, "403 upload must not leave a media row behind"

    # And a retry does NOT lie 'stored=True' via the duplicate fast-path — it
    # is judged on its own merits (still 403, still foreign batch).
    r2 = await client.post(
        "/api/v1/media",
        files={"file": ("p.jpg", io.BytesIO(_JPEG), "image/jpeg")},
        headers=_headers(),
    )
    assert r2.status_code == 403, r2.text
