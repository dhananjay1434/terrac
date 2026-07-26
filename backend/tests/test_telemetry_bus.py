"""M2.4 — telemetry pub/sub bus + stream tickets (pure, unit-tested).

The SSE HTTP endpoints (M2.4 shell) get smoke tests only; the real logic lives
here where it is deterministic (injectable clock, no event-loop gymnastics for
the ticket path).
"""
import asyncio

import pytest

import telemetry_bus as bus
from telemetry_bus import (
    mint_ticket,
    publish,
    redeem_ticket,
    subscribe,
    unsubscribe,
)


@pytest.fixture(autouse=True)
def _clean_state():
    bus._subscribers.clear()
    bus._tickets.clear()
    yield
    bus._subscribers.clear()
    bus._tickets.clear()


# ── pub/sub ────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_publish_reaches_subscriber():
    q = subscribe("batch-1")
    assert publish("batch-1", {"channel": "T1", "v": 412.5}) == 1
    frame = await q.get()
    assert frame["channel"] == "T1"


@pytest.mark.asyncio
async def test_publish_with_no_subscribers_is_zero():
    assert publish("nobody-home", {"v": 1}) == 0


@pytest.mark.asyncio
async def test_publish_fans_out_to_many():
    a = subscribe("batch-2")
    b = subscribe("batch-2")
    assert publish("batch-2", {"v": 1}) == 2
    assert (await a.get())["v"] == 1
    assert (await b.get())["v"] == 1


@pytest.mark.asyncio
async def test_unsubscribe_cleans_up_and_removes_empty_batch():
    q = subscribe("batch-3")
    unsubscribe("batch-3", q)
    assert "batch-3" not in bus._subscribers
    assert publish("batch-3", {"v": 1}) == 0


@pytest.mark.asyncio
async def test_full_queue_drops_frame_never_raises():
    q = subscribe("batch-4")
    # fill beyond capacity — publish must not raise and must count only delivered
    for _ in range(bus._QUEUE_MAX):
        q.put_nowait({"v": 0})
    assert publish("batch-4", {"v": 1}) == 0  # queue full → dropped, no exception


# ── tickets ────────────────────────────────────────────────────────────────
def test_ticket_single_use():
    t = mint_ticket("batch-5")
    assert redeem_ticket(t, "batch-5") is True
    assert redeem_ticket(t, "batch-5") is False  # consumed


def test_ticket_valid_within_ttl():
    t = mint_ticket("batch-6", ttl=10, now=1000.0)
    assert redeem_ticket(t, "batch-6", now=1005.0) is True


def test_ticket_expired_rejected():
    t = mint_ticket("batch-7", ttl=10, now=1000.0)
    assert redeem_ticket(t, "batch-7", now=1011.0) is False


def test_ticket_wrong_batch_rejected_and_consumed():
    t = mint_ticket("batch-8")
    assert redeem_ticket(t, "batch-WRONG") is False
    assert redeem_ticket(t, "batch-8") is False  # popped even on wrong-batch


def test_unknown_ticket_rejected():
    assert redeem_ticket("never-minted", "batch-9") is False


def test_mint_sweeps_expired_tickets():
    old = mint_ticket("batch-10", ttl=10, now=1000.0)
    # minting later than the old ticket's expiry should GC it
    mint_ticket("batch-11", ttl=10, now=2000.0)
    assert old not in bus._tickets
