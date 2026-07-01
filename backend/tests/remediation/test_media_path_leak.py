from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64
import json
import pytest
import uuid
from httpx import AsyncClient
import pytest_asyncio

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def registered_device(client: AsyncClient, session_factory):
    from models import EnrollmentToken
    import base64

    async with session_factory() as session:
        t = EnrollmentToken(token="test-credit-leak")
        session.add(t)
        await session.commit()

    b64_key = TEST_PUBLIC_KEY_B64
    dev_id = "test-device-leak"
    payload = {"device_id": dev_id, "public_key": b64_key}
    headers = {"X-Enrollment-Token": "test-credit-leak"}
    await client.post(
        "/api/v1/register", content=json.dumps(payload).encode("utf-8"), headers=headers
    )

    return {"device_id": dev_id, "b64_key": b64_key}


async def test_media_endpoint_does_not_leak_absolute_path(
    client: AsyncClient, registered_device
):
    from tests.remediation.crypto_utils import sign_request
    import hashlib
    import tempfile
    import os

    dev_id = registered_device["device_id"]

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"leak test")
        tmp_name = tmp.name

    actual_hash = hashlib.sha256(b"leak test").hexdigest()

    with open(tmp_name, "rb") as f:
        resp = await client.post(
            "/api/v1/media",
            files={"file": ("photo.jpg", f, "image/jpeg")},
            headers={
                "X-Idempotency-Key": "op-media-leak",
                "X-Declared-SHA256": actual_hash,
                "X-Batch-UUID": str(uuid.uuid4()),
                "X-Device-Id": dev_id,
                "X-Signature": "dummy",  # mock will skip if dummy
            },
        )
    assert resp.status_code == 200

    data = resp.json()
    file_path = data["file_path"]

    # Assert it's just the basename, not containing any slashes or backslashes
    assert "/" not in file_path
    assert "\\" not in file_path
    assert file_path.startswith("op-media-leak.")
