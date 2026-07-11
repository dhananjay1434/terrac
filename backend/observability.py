"""P3.4 — backend observability: structured logs, request IDs, metrics, Sentry.

All four concerns live here so server.py only wires a middleware, a /metrics
route, and a startup call. prometheus_client and sentry_sdk are imported
defensively — if a dep is absent the app still boots (metrics degrade to 503,
Sentry is a no-op), so the default local/test path needs neither installed.

PII policy (mirror of the Flutter client's beforeBreadcrumb): latitude,
longitude and device_id must never leave the process in a breadcrumb or event.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import time
import uuid
from typing import Optional

# --- request-id context -----------------------------------------------------
# Bound per-request in the middleware; read by the log formatter so every line
# emitted while handling a request carries its id, with zero call-site changes.
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)

# Fields we refuse to emit anywhere (logs, Sentry breadcrumbs/events).
_PII_KEYS = ("lat", "lon", "latitude", "longitude", "device_id", "x-device-id")


# ===========================================================================
# 1. Structured JSON logging
# ===========================================================================
class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_ctx.get(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        # Allow structured extras without crashing on non-serializable values.
        for k, v in getattr(record, "__dict__", {}).items():
            if k == "extra_fields" and isinstance(v, dict):
                for ek, ev in v.items():
                    if ek.lower() not in _PII_KEYS:
                        payload[ek] = ev
        return json.dumps(payload, default=str)


def configure_json_logging(level: Optional[str] = None) -> None:
    """Install the JSON formatter on the root logger. Idempotent — safe to call
    from a reloaded module or repeatedly in tests."""
    lvl = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(lvl)
    # Replace any existing handlers with a single JSON stream handler.
    for h in list(root.handlers):
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.set_name("dmrv-json")
    root.addHandler(handler)
    # Route uvicorn's access/error loggers through the same handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True


# ===========================================================================
# 2. Prometheus metrics
# ===========================================================================
try:  # prometheus is optional at runtime
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROM = True
except Exception:  # pragma: no cover - only when the dep is absent
    _PROM = False
    CONTENT_TYPE_LATEST = "text/plain"

if _PROM:
    REQUEST_COUNT = Counter(
        "dmrv_requests_total",
        "HTTP requests by method, route template, and status.",
        ["method", "route", "status"],
    )
    REQUEST_LATENCY = Histogram(
        "dmrv_request_duration_seconds",
        "Request latency by route template.",
        ["route"],
    )
    SYNC_5XX = Counter(
        "dmrv_sync_5xx_total",
        "5xx responses on /api/ endpoints (device-sync failure signal).",
        ["route"],
    )
    PROVISIONAL_RATIO = Gauge(
        "dmrv_provisional_ratio",
        "Fraction of batches currently provisional (0..1).",
    )
    RECOMPUTE_DURATION = Histogram(
        "dmrv_recompute_duration_seconds",
        "Wall time of recompute_batch_credit.",
    )
    CANONICAL_V1 = Counter(
        "dmrv_canonical_v1_requests_total",
        "Verified requests using the v1 (unversioned) signature canonical. Flip "
        "DMRV_REQUIRE_CANONICAL_V2 on only after this stays zero across the fleet "
        "(P4.2).",
        ["route"],
    )


def _route_template(request) -> str:
    """The matched route's path template (bounded cardinality), not the raw URL
    (which carries UUIDs and would explode label cardinality)."""
    route = request.scope.get("route")
    tmpl = getattr(route, "path", None)
    return tmpl or "unmatched"


def record_request(request, status_code: int, duration_s: float) -> None:
    if not _PROM:
        return
    route = _route_template(request)
    REQUEST_COUNT.labels(request.method, route, str(status_code)).inc()
    REQUEST_LATENCY.labels(route).observe(duration_s)
    if status_code >= 500 and request.url.path.startswith("/api/"):
        SYNC_5XX.labels(route).inc()


def observe_recompute(duration_s: float) -> None:
    if _PROM:
        RECOMPUTE_DURATION.observe(duration_s)


def record_canonical_v1(route: str) -> None:
    """Count a verified request that used the legacy v1 signature canonical."""
    if _PROM:
        CANONICAL_V1.labels(route).inc()


def timed_recompute(fn):
    """Decorator: time an async recompute into RECOMPUTE_DURATION."""
    import functools

    @functools.wraps(fn)
    async def _wrap(*a, **k):
        t0 = time.perf_counter()
        try:
            return await fn(*a, **k)
        finally:
            observe_recompute(time.perf_counter() - t0)

    return _wrap


def set_provisional_ratio(ratio: float) -> None:
    if _PROM:
        PROVISIONAL_RATIO.set(ratio)


def metrics_enabled() -> bool:
    return _PROM


def require_metrics_token(supplied: Optional[str]) -> None:
    """Guard /metrics. A public scrape leaks operational intel, so a token is
    mandatory: if DMRV_METRICS_TOKEN is unset the endpoint is closed entirely."""
    from fastapi import HTTPException

    expected = os.environ.get("DMRV_METRICS_TOKEN", "")
    if not expected or not supplied or not _consteq(supplied, expected):
        raise HTTPException(status_code=401, detail="metrics_unauthorized")


def _consteq(a: str, b: str) -> bool:
    import hmac

    return hmac.compare_digest(a.encode(), b.encode())


def metrics_payload():
    """Return a FastAPI Response with the current metric exposition."""
    from fastapi import Response

    if not _PROM:
        return Response("metrics unavailable", status_code=503)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ===========================================================================
# 3. Request-context middleware (id + timing + metrics)
# ===========================================================================
def install_middleware(app) -> None:
    @app.middleware("http")
    async def _observability(request, call_next):
        rid = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        token = request_id_ctx.set(rid)
        t0 = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Record the failure, then let the app's handlers turn it into a
            # 500 — never swallow the exception.
            record_request(request, 500, time.perf_counter() - t0)
            logging.getLogger("dmrv").exception("unhandled_error")
            raise
        finally:
            request_id_ctx.reset(token)
        record_request(request, response.status_code, time.perf_counter() - t0)
        response.headers["X-Request-Id"] = rid
        return response


# ===========================================================================
# 4. Sentry
# ===========================================================================
def _scrub_event(event, hint):  # pragma: no cover - exercised only with a DSN
    """Strip PII from Sentry events + breadcrumbs before they leave the process."""

    def _clean(d):
        if not isinstance(d, dict):
            return d
        for k in list(d.keys()):
            if k.lower() in _PII_KEYS:
                d[k] = "[scrubbed]"
            elif isinstance(d[k], dict):
                _clean(d[k])
        return d

    if isinstance(event, dict):
        _clean(event.get("request", {}).get("headers", {}))
        _clean(event.get("extra", {}))
        _clean(event.get("contexts", {}))
        for bc in event.get("breadcrumbs", {}).get("values", []) if isinstance(
            event.get("breadcrumbs"), dict
        ) else []:
            _clean(bc.get("data", {}))
    return event


def init_sentry() -> bool:
    """Initialize Sentry if a DSN is configured and the SDK is installed."""
    dsn = os.environ.get("DMRV_SENTRY_DSN", "").strip()
    if not dsn:
        return False
    try:  # pragma: no cover - only when sentry-sdk is installed + DSN set
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=dsn,
            traces_sample_rate=float(os.environ.get("DMRV_SENTRY_TRACES", "0.05")),
            integrations=[StarletteIntegration(), FastApiIntegration()],
            before_send=_scrub_event,
            before_breadcrumb=lambda bc, hint: _scrub_event({"extra": bc.get("data", {})}, hint)
            and bc,
            send_default_pii=False,
            environment=os.environ.get("DMRV_ENV", "production"),
        )
        return True
    except Exception:
        logging.getLogger("dmrv").warning("sentry init failed; continuing without it")
        return False
