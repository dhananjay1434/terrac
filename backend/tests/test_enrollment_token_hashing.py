"""Audit fix 6: enrollment tokens are stored hashed; raw legacy rows still work."""

import hashlib
import json
import uuid

import pytest
from sqlalchemy import select

from models import EnrollmentToken
from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64

pytestmark = pytest.mark.asyncio

ADMIN = {"X-Admin-Secret": "test-admin-secret"}


async def test_minted_token_stored_hashed_and_usable(client, session_factory):
    raw = "tok-" + uuid.uuid4().hex
    r = await client.post(
        "/api/v1/admin/mint-token",
        content=json.dumps({"token": raw, "expires_in_days": 1}).encode("utf-8"),
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text
    assert r.json()["token"] == raw          # raw returned once to the operator

    # DB stores ONLY the hash.
    h = hashlib.sha256(raw.encode()).hexdigest()
    async with session_factory() as s:
        assert (
            await s.execute(select(EnrollmentToken).where(EnrollmentToken.token == h))
        ).scalar_one_or_none() is not None
        assert (
            await s.execute(select(EnrollmentToken).where(EnrollmentToken.token == raw))
        ).scalar_one_or_none() is None

    # And the raw token still enrolls a device (server hashes on lookup).
    r2 = await client.post(
        "/api/v1/register",
        content=json.dumps(
            {"device_id": "dev-" + uuid.uuid4().hex[:8], "public_key": TEST_PUBLIC_KEY_B64}
        ).encode("utf-8"),
        headers={"X-Enrollment-Token": raw},
    )
    assert r2.status_code == 201, r2.text
