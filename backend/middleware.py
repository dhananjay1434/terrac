from __future__ import annotations
import os
import time
from fastapi import Request, status
from fastapi.responses import JSONResponse
from settings import _rl_int, env_int

# Phase 11-R: reject oversized bodies via Content-Length before parsing. JSON
# endpoints are capped at 2 MB (a max 100k-float telemetry log is well under that);
# /api/v1/media gets headroom for its multipart 10 MB file (its handler enforces the
# real 10 MB cap while streaming).
_MAX_JSON_BODY_BYTES = 2 * 1024 * 1024
_MAX_MEDIA_BODY_BYTES = 12 * 1024 * 1024
async def _limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl is not None and cl.isdigit():
        cap = (
            _MAX_MEDIA_BODY_BYTES
            if request.url.path == "/api/v1/media"
            else _MAX_JSON_BODY_BYTES
        )
        if int(cl) > cap:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={"detail": "payload_too_large"},
            )
    return await call_next(request)
# ==================== T2.2: per-route rate limiting ====================
# Fixed-window counter keyed by (bucket, device-or-ip). In-process — correct for
# a single-node pilot; swap to a shared store (Redis) when horizontally scaled
# (tracked in the T3 roadmap). Register/admin are IP-keyed brute-force surfaces;
# media/default are device-keyed throughput limits.
#
# Config is read LIVE from os.environ on every request (not captured at import),
# so it survives importlib.reload(server) — a test elsewhere reloads this module,
# which would otherwise desync module-level constants from the running middleware.
# It also makes every limit + the window genuinely runtime-tunable. Disabled by
# default under test (conftest sets DMRV_RATELIMIT_ENABLED=0); test_rate_limit.py
# re-enables it via monkeypatch.setenv.
_RL_DEFAULT_CAPS = {"register": 5, "admin": 30, "media": 20, "default": 120}
_RL_CAP_ENV = {
    "register": "DMRV_RATELIMIT_REGISTER",
    "admin": "DMRV_RATELIMIT_ADMIN",
    "media": "DMRV_RATELIMIT_MEDIA",
    "default": "DMRV_RATELIMIT_DEFAULT",
}
# {(bucket, key, window_index): count} — bounded by pruning when it grows large.
_rl_counters: dict = {}
_RL_MAX_COUNTERS = 4096
def _rl_prune(current_window: int) -> None:
    """P3.7/M1: bound memory WITHOUT wiping live windows.

    The previous ``_rl_counters.clear()`` at the cap was an attack surface: a
    flooder could push the dict past the cap and reset EVERYONE's current-window
    counters to zero, defeating the limiter. Instead, drop only dead windows
    (older than the current one); if still over cap, evict the oldest windows
    first. Current-window counts always survive.
    """
    stale = [k for k in _rl_counters if k[2] < current_window]
    for k in stale:
        del _rl_counters[k]
    if len(_rl_counters) > _RL_MAX_COUNTERS:
        # Still over cap with only live/future windows — evict oldest-window
        # entries first (lowest window index) until back under the cap.
        for k in sorted(_rl_counters, key=lambda kk: kk[2])[
            : len(_rl_counters) - _RL_MAX_COUNTERS
        ]:
            del _rl_counters[k]
def _rl_enabled() -> bool:
    return os.environ.get("DMRV_RATELIMIT_ENABLED", "1") == "1"
def _rl_window_seconds() -> int:
    return max(1, _rl_int("DMRV_RATELIMIT_WINDOW_SECONDS", 60))
def _rl_now() -> int:
    """Current epoch seconds — isolated so it can be stubbed if ever needed."""
    return int(time.time())
def _rl_bucket(path: str) -> str:
    if path == "/api/v1/register":
        return "register"
    # P2.1: portal auth/admin surfaces are brute-force targets — rate-limit them
    # under the stricter "admin" bucket (keyed by client IP).
    if path.startswith("/api/v1/admin/") or path.startswith(
        "/api/v1/portal/"
    ) or path.endswith("/compliance"):
        return "admin"
    if path == "/api/v1/media":
        return "media"
    return "default"
async def _rate_limit(request: Request, call_next):
    if not _rl_enabled() or request.method == "OPTIONS":
        return await call_next(request)
    path = request.url.path
    if not path.startswith("/api/") or path == "/api/health":
        return await call_next(request)
    bucket = _rl_bucket(path)
    cap = _rl_int(_RL_CAP_ENV[bucket], _RL_DEFAULT_CAPS[bucket])
    if bucket in ("register", "admin"):
        # brute-force surfaces: key by client IP so rotating device ids can't evade.
        # Behind a TLS-terminating proxy the socket peer is the proxy, so prefer
        # the first X-Forwarded-For hop when present (uvicorn --proxy-headers
        # already rewrites request.client; this is belt-and-braces for runs
        # without that flag). First hop = client as seen by OUR proxy.
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            key = fwd.split(",")[0].strip() or "ip-unknown"
        else:
            key = request.client.host if request.client else "ip-unknown"
    else:
        # Key by client IP, NOT the client-supplied X-Device-Id: the device id
        # is unauthenticated at middleware time (signature auth runs later), so
        # rotating it must not mint fresh buckets and evade the cap. Prefer the
        # first X-Forwarded-For hop (Task 1) so the limit tracks the real client
        # behind Render's proxy. Tradeoff: devices behind one NAT share a
        # bucket — acceptable for an abuse limit; per-device throughput is
        # enforced after auth.
        fwd = request.headers.get("x-forwarded-for")
        key = (
            fwd.split(",")[0].strip()
            if fwd
            else (request.client.host if request.client else "unknown")
        )
    window_seconds = _rl_window_seconds()
    now = _rl_now()
    window = now // window_seconds
    ckey = (bucket, key, window)
    if len(_rl_counters) > 4096:
        _rl_prune(window)
    count = _rl_counters.get(ckey, 0) + 1
    _rl_counters[ckey] = count
    if count > cap:
        retry = window_seconds - (now % window_seconds)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "rate_limited"},
            headers={"Retry-After": str(max(1, retry))},
        )
    return await call_next(request)
