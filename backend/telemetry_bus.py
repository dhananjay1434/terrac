"""Single-process pub/sub + stream tickets for live burn telemetry (M2.4).

Correct for the current single-worker uvicorn deployment (see the Dockerfile
CMD). When workers > 1, swap the internals for Redis pub/sub + a shared ticket
store — the public interface (subscribe/unsubscribe/publish, mint_ticket/
redeem_ticket) stays identical. Zero FastAPI imports so it is trivially
unit-testable; the SSE endpoint (M2.4 HTTP layer) is a thin shell over this.

Auth model (audit A1): the browser EventSource API cannot send an Authorization
header, so a bearer-authed POST mints a short-TTL, single-use, batch-bound
ticket which the GET stream redeems. The token never rides in a logged header.
"""
from __future__ import annotations

import asyncio
import secrets
import time

# batch_uuid -> set of live subscriber queues
_subscribers: dict[str, set[asyncio.Queue]] = {}
# ticket -> (batch_uuid, expiry_monotonic)
_tickets: dict[str, tuple[str, float]] = {}

TICKET_TTL_S = 60.0
_QUEUE_MAX = 1000  # backpressure: a slow client drops frames, never blocks ingest


def subscribe(batch_uuid: str) -> asyncio.Queue:
    """Register a live listener for a batch's telemetry. Caller MUST pair every
    subscribe() with an unsubscribe() (the SSE handler does this in finally)."""
    q: asyncio.Queue = asyncio.Queue(maxsize=_QUEUE_MAX)
    _subscribers.setdefault(batch_uuid, set()).add(q)
    return q


def unsubscribe(batch_uuid: str, q: asyncio.Queue) -> None:
    subs = _subscribers.get(batch_uuid)
    if subs is None:
        return
    subs.discard(q)
    if not subs:
        _subscribers.pop(batch_uuid, None)


def publish(batch_uuid: str, payload: dict) -> int:
    """Fan a telemetry frame out to every live subscriber. Returns the number
    delivered. Never raises on a full queue — ingest must not be coupled to the
    liveness of any viewer."""
    subs = _subscribers.get(batch_uuid)
    if not subs:
        return 0
    delivered = 0
    for q in list(subs):
        try:
            q.put_nowait(payload)
            delivered += 1
        except asyncio.QueueFull:
            pass  # slow consumer drops this frame; the next read reconciles
    return delivered


def _sweep_expired(now: float) -> None:
    """Opportunistic GC so unredeemed tickets can't grow unbounded."""
    dead = [t for t, (_, exp) in _tickets.items() if now > exp]
    for t in dead:
        _tickets.pop(t, None)


def mint_ticket(
    batch_uuid: str, *, ttl: float = TICKET_TTL_S, now: float | None = None
) -> str:
    """Issue a single-use, batch-bound, TTL-limited stream ticket. `now` is
    injectable for deterministic tests (else monotonic clock)."""
    clock = time.monotonic() if now is None else now
    _sweep_expired(clock)
    ticket = secrets.token_urlsafe(32)
    _tickets[ticket] = (batch_uuid, clock + ttl)
    return ticket


def redeem_ticket(
    ticket: str, batch_uuid: str, *, now: float | None = None
) -> bool:
    """Validate + consume a ticket. Pops on ANY outcome (success, expiry, wrong
    batch) so a ticket can never be replayed. Returns True only when the live,
    unexpired ticket was bound to exactly this batch."""
    entry = _tickets.pop(ticket, None)
    if entry is None:
        return False
    bound_batch, expiry = entry
    clock = time.monotonic() if now is None else now
    if clock > expiry:
        return False
    return bound_batch == batch_uuid
