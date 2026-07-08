import pytest


@pytest.mark.asyncio
async def test_lifespan_starts_db(client):
    # /api/health must respond 200 through the app. T2.6 made the endpoint probe
    # the DB (Depends(get_session)); the shared `client` fixture supplies the
    # overridden per-test session, so this exercises the real request path
    # without binding the module engine to a throwaway event loop.
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["db"] == "ok"
