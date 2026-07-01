from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64

"""Phase 3 — enrollment tokens are single-use; the `dev-token` backdoor is gone.

A freshly minted token enrolls a device exactly once (201). Reusing the same
token is rejected (401 enrollment_token_used). Uses the shared `client` fixture
+ in-memory DB from conftest.py.
"""

import base64
import json

import pytest

# 32-byte raw key -> base64url (44 chars), within RegistrationRequest's 40..64 bound.
_B64_KEY = TEST_PUBLIC_KEY_B64


async def _mint(client, token: str) -> int:
    resp = await client.post(
        "/api/v1/admin/mint-token",
        content=json.dumps({"token": token, "expires_in_days": 7}).encode("utf-8"),
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
    return resp.status_code


async def _register(client, device_id: str, token: str):
    return await client.post(
        "/api/v1/register",
        content=json.dumps({"device_id": device_id, "public_key": _B64_KEY}).encode(
            "utf-8"
        ),
        headers={"X-Enrollment-Token": token},
    )


@pytest.mark.asyncio
async def test_minted_token_enrolls_device_once(client):
    assert await _mint(client, "enroll-tok-1") == 201
    r1 = await _register(client, "dev-enroll-1", "enroll-tok-1")
    assert r1.status_code == 201


@pytest.mark.asyncio
async def test_token_reuse_is_rejected(client):
    assert await _mint(client, "enroll-tok-2") == 201
    r1 = await _register(client, "dev-enroll-2a", "enroll-tok-2")
    assert r1.status_code == 201

    r2 = await _register(client, "dev-enroll-2b", "enroll-tok-2")
    assert r2.status_code == 401
    assert r2.json()["detail"] == "enrollment_token_used"
