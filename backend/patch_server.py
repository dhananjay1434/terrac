
with open('server.py', 'a', encoding='utf-8') as f:
    f.write('''

# R8: routers and middleware
from middleware import _limit_body_size, _rate_limit, _RL_MAX_COUNTERS, _rl_counters  # noqa: F401
app.middleware("http")(_limit_body_size)
app.middleware("http")(_rate_limit)
import observability
observability.install_middleware(app)

from routers.health import router as health_router
from routers.devices import router as devices_router
from routers.batches import router as batches_router
from routers.evidence import router as evidence_router
from routers.media import router as media_router
from routers.lab import router as lab_router
from routers.admin import router as admin_router
from routers.compliance import router as compliance_router

app.include_router(health_router)
app.include_router(devices_router)
app.include_router(batches_router)
app.include_router(evidence_router)
app.include_router(media_router)
app.include_router(lab_router)
app.include_router(admin_router)
app.include_router(compliance_router)
''')
