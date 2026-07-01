"""Phase 2 — the admin endpoint must authenticate against a dedicated
DMRV_ADMIN_SECRET, never the HMAC pepper (DMRV_HMAC_SECRET).

Uses the shared `client` fixture + in-memory DB from conftest.py. The conftest
sets DMRV_HMAC_SECRET="test-secret" and DMRV_ADMIN_SECRET="test-admin-secret"
before `server` is imported.
"""

import json

import pytest


@pytest.mark.asyncio
async def test_mint_rejects_hmac_pepper_as_admin(client):
    # The HMAC pepper must NOT authenticate as admin.
    r = await client.post(
        "/api/v1/admin/mint-token",
        content=json.dumps({"token": "tok-pepper", "expires_in_days": 7}).encode(
            "utf-8"
        ),
        headers={"X-Admin-Secret": "test-secret"},  # == DMRV_HMAC_SECRET
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_mint_accepts_dedicated_admin_secret(client):
    # The dedicated admin secret works.
    r = await client.post(
        "/api/v1/admin/mint-token",
        content=json.dumps({"token": "tok-admin", "expires_in_days": 7}).encode(
            "utf-8"
        ),
        headers={"X-Admin-Secret": "test-admin-secret"},  # == DMRV_ADMIN_SECRET
    )
    assert r.status_code == 201
