"""P2.0 — portal APIRouter seam.

The app must boot with the portal router mounted, and the temporary auth-free
`/api/v1/portal/ping` must return 200. This proves new portal code can hang off
its own module without touching server.py beyond the single mount line.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def test_portal_router_mounted(client):
    # The temporary /ping was removed in P2.1; the real /login route proves the
    # router is still mounted (422 for an invalid body, never 404).
    r = await client.post("/api/v1/portal/login", json={})
    assert r.status_code == 422


async def test_health_still_ok(client):
    # The seam must not disturb the existing device-facing app.
    r = await client.get("/api/health")
    assert r.status_code == 200
