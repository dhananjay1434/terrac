"""Phase 1 — media_files.capture_type + optional X-Capture-Type hint header.

The header is a client-authored HINT (NOT in the frozen Ed25519 media canonical),
so it lands with capture_type_verified=False. Omitting it leaves legacy clients
unaffected (capture_type NULL). A malformed value is rejected 400 with no row left
behind (audit fix 3).
"""

import hashlib
import io
import uuid

import pytest
from sqlalchemy import select

from models import MediaFile
from tests.remediation.crypto_utils import sign_media

pytestmark = pytest.mark.asyncio

DEVICE = "test-device-reg"  # seeded + enrolled by conftest


def _file(content: bytes):
    return {"file": ("p.jpg", io.BytesIO(content), "image/jpeg")}


async def test_capture_type_hint_stored_unverified(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"flame-curtain-photo"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Capture-Type": "flame_curtain",
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 200, r.text

    async with session_factory() as s:
        m = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one()
        assert m.capture_type == "flame_curtain"
        assert m.capture_type_verified is False


async def test_end_use_capture_type_accepted_and_stored_unverified(client, registered_device, session_factory):
    """V5: the farmer end-use photo is now stamped `end_use` at the app layer
    and forwarded the same way flame_curtain etc. always were — the header
    validator has no per-value allowlist, so this is the closing regression
    test locking `end_use` into the accepted vocabulary end-to-end."""
    bu = str(uuid.uuid4())
    content = b"farmer-end-use-photo"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Capture-Type": "end_use",
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 200, r.text

    async with session_factory() as s:
        m = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one()
        assert m.capture_type == "end_use"
        assert m.capture_type_verified is False


async def test_no_header_leaves_capture_type_null(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"legacy-client-photo"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 200, r.text

    async with session_factory() as s:
        m = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one()
        assert m.capture_type is None
        assert m.capture_type_verified is False


async def test_malformed_capture_type_400_no_row(client, registered_device, session_factory):
    bu = str(uuid.uuid4())
    content = b"bad-capture-type-photo"
    sha = hashlib.sha256(content).hexdigest()
    op = "m-" + uuid.uuid4().hex[:8]
    r = await client.post(
        "/api/v1/media",
        files=_file(content),
        headers={
            "X-Idempotency-Key": op,
            "X-Declared-SHA256": sha,
            "X-Batch-UUID": bu,
            "X-Device-Id": DEVICE,
            "X-Capture-Type": "Fla me!",
            "X-Signature": sign_media(DEVICE, op, sha, bu),
        },
    )
    assert r.status_code == 400, r.text
    assert "invalid_capture_type" in r.text

    async with session_factory() as s:
        m = (
            await s.execute(select(MediaFile).where(MediaFile.operation_id == op))
        ).scalar_one_or_none()
        assert m is None
