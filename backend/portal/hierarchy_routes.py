"""M1.5 (hierarchy_v2) — cascading network→site→kiln hierarchy for portal filters.

GET /api/v1/portal/hierarchy →
  {"networks": [{"network_id","name","sites":[{"site_id","name",
     "kilns":[{"kiln_id","kiln_code","sensor_profile"}]}]}]}

Feature-flagged (hierarchy_v2): when the flag is OFF the endpoint returns an
empty list, so the capability stays fully dormant until enabled per org
(Global Rule 8). Its own thin router (like issuance_routes), mounted under the
same /api/v1/portal prefix.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_session
from feature_flags import flag_enabled
from models import Facility, Kiln, Network, PortalUser

from .auth import require_role

router = APIRouter(prefix="/api/v1/portal", tags=["portal-hierarchy"])


@router.get("/hierarchy")
async def get_hierarchy(
    user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    if not await flag_enabled(session, "hierarchy_v2", user.org_id):
        return {"networks": []}

    net_q = select(Network)
    if user.org_id:  # light org scope: this org's networks + global/unscoped ones
        net_q = net_q.where(
            (Network.org_id == user.org_id) | (Network.org_id.is_(None))
        )
    networks = (await session.execute(net_q)).scalars().all()
    facilities = (await session.execute(select(Facility))).scalars().all()
    kilns = (await session.execute(select(Kiln))).scalars().all()

    kilns_by_site: dict[str, list] = {}
    for k in kilns:
        if k.site_id:
            kilns_by_site.setdefault(k.site_id, []).append(k)
    sites_by_network: dict[str, list] = {}
    for f in facilities:
        if f.network_id:
            sites_by_network.setdefault(f.network_id, []).append(f)

    out = []
    for n in networks:
        sites = [
            {
                "site_id": f.facility_uuid,
                "name": f.name,
                "kilns": [
                    {
                        "kiln_id": k.kiln_id,
                        "kiln_code": k.kiln_code,
                        "sensor_profile": k.sensor_profile,
                    }
                    for k in kilns_by_site.get(f.facility_uuid, [])
                ],
            }
            for f in sites_by_network.get(n.network_id, [])
        ]
        out.append({"network_id": n.network_id, "name": n.name, "sites": sites})
    return {"networks": out}
