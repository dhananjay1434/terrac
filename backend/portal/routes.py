"""Portal API router.

Mounted once from `server.py` via `app.include_router(router)`. Every new
portal endpoint (auth, batch read API, lab/verifier flows) hangs off THIS
router — `server.py` only ever gains the single mount line.
"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@router.get("/ping")
async def ping() -> dict:
    """Temporary seam probe — proves the router is wired. Removed in P2.1 once
    real portal endpoints exist."""
    return {"status": "ok"}
