import os
import pytest
from httpx import AsyncClient, ASGITransport

# We need to reload the app with the env var set
def reload_app_with_cors(origin: str):
    os.environ["DMRV_ALLOWED_ORIGIN"] = origin
    # Import the app module dynamically to pick up the env var
    import importlib
    import server
    importlib.reload(server)
    return server.app

@pytest.mark.asyncio
async def test_cors_hardened(monkeypatch):
    monkeypatch.setenv("DMRV_ALLOWED_ORIGIN", "https://trusted-domain.com")
    import importlib
    import server
    importlib.reload(server)
    
    app = server.app
    transport = ASGITransport(app=app)
    
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Preflight request
        response = await ac.options("/api/health", headers={
            "Origin": "https://trusted-domain.com",
            "Access-Control-Request-Method": "POST",
        })
        assert response.status_code == 200
        assert response.headers.get("access-control-allow-origin") == "https://trusted-domain.com"
        
        # Test rejected origin
        response = await ac.options("/api/health", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST",
        })
        assert response.headers.get("access-control-allow-origin") != "https://evil.com"
