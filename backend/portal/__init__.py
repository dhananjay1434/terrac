"""Lab & Verifier portal (P2).

New portal-facing backend code lives in this package — auth, read/write routes,
and schemas — so `server.py` (the device-facing monolith) stops growing. The
seam is a single `APIRouter` mounted from `server.py`; existing routes stay put
and are migrated out one group per commit under P4.8.
"""
