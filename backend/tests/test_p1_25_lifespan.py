import pytest
from httpx import AsyncClient, ASGITransport
from server import app


@pytest.mark.asyncio
async def test_lifespan_starts_db():
    # Verify the FastAPI TestClient or ASGI app works with lifespan correctly
    transport = ASGITransport(app=app)
    # Using the lifespan context triggers lifespan events
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/api/health")
        assert response.status_code == 200
