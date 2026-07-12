"""P3.7 — recompute coalescing + rate-limit pruning.

Rate limit: the old clear-all-at-cap let a flooder wipe everyone's live window;
pruning must keep current-window counts. Recompute: a burst of concurrent
posts coalesces to fewer runs, but spaced-out posts each still run (never drop a
needed recompute).
"""

import asyncio
from types import SimpleNamespace

import pytest

import server
import credit_engine


# --------------------------------------------------------------------------
# M1 — rate-limit pruning keeps live windows
# --------------------------------------------------------------------------
def test_prune_drops_stale_windows_keeps_current():
    server._rl_counters.clear()
    current = 1000
    # Stale windows (older) + a live current-window counter under attack.
    for i in range(50):
        server._rl_counters[("default", f"dev{i}", current - 1)] = 7
    server._rl_counters[("register", "attacker-ip", current)] = 4

    server._rl_prune(current)

    # Every stale entry is gone; the current-window count SURVIVES intact.
    assert all(k[2] >= current for k in server._rl_counters)
    assert server._rl_counters[("register", "attacker-ip", current)] == 4


def test_prune_evicts_oldest_first_when_all_live():
    server._rl_counters.clear()
    # No stale entries — spread across increasing windows; force over-cap eviction.
    cap = server._RL_MAX_COUNTERS
    for w in range(cap + 100):
        server._rl_counters[("default", "k", w)] = 1
    newest = cap + 99
    server._rl_prune(newest)
    assert len(server._rl_counters) <= cap
    # The newest window must not be the one evicted.
    assert ("default", "k", newest) in server._rl_counters
    # The very oldest window should have been dropped.
    assert ("default", "k", 0) not in server._rl_counters


# --------------------------------------------------------------------------
# H2 — recompute coalescing
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_posts_coalesce(monkeypatch):
    calls = {"n": 0}

    async def _fake_impl(session, batch, **kw):
        calls["n"] += 1
        await asyncio.sleep(0.02)  # hold the lock so others pile up behind it

    monkeypatch.setattr(credit_engine, "_recompute_batch_credit_impl", _fake_impl)
    buid = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    server._recompute_state.pop(buid, None)
    batch = SimpleNamespace(batch_uuid=buid)

    n = 8
    await asyncio.gather(
        *[server.recompute_batch_credit(None, batch, coalesce=True) for _ in range(n)]
    )

    assert 1 <= calls["n"] < n  # collapsed, but at least one ran
    # A recompute ran after the last caller marked the batch dirty.
    assert server._recompute_state[buid]["dirty"] is False


@pytest.mark.asyncio
async def test_spaced_posts_each_recompute(monkeypatch):
    """Coalescing must NOT drop a recompute when calls don't overlap."""
    calls = {"n": 0}

    async def _fake_impl(session, batch, **kw):
        calls["n"] += 1

    monkeypatch.setattr(credit_engine, "_recompute_batch_credit_impl", _fake_impl)
    buid = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    server._recompute_state.pop(buid, None)
    batch = SimpleNamespace(batch_uuid=buid)

    for _ in range(4):
        await server.recompute_batch_credit(None, batch, coalesce=True)
    assert calls["n"] == 4


@pytest.mark.asyncio
async def test_pre_commit_path_never_coalesces(monkeypatch):
    """coalesce=False callers (create_batch/lab) always run, even concurrently."""
    calls = {"n": 0}

    async def _fake_impl(session, batch, **kw):
        calls["n"] += 1
        await asyncio.sleep(0.01)

    monkeypatch.setattr(credit_engine, "_recompute_batch_credit_impl", _fake_impl)
    buid = "cccccccc-cccc-cccc-cccc-cccccccccccc"
    server._recompute_state.pop(buid, None)
    batch = SimpleNamespace(batch_uuid=buid)

    n = 5
    await asyncio.gather(
        *[server.recompute_batch_credit(None, batch) for _ in range(n)]
    )
    assert calls["n"] == n  # every pre-commit caller ran


# --------------------------------------------------------------------------
# H3 — large telemetry payloads parse off-thread
# --------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_big_payload_parsed_off_thread():
    import json

    big = json.dumps({"temperature_log": [float(i) for i in range(80_000)]})
    assert len(big) > server._BIG_JSON_BYTES
    parsed = await server._safe_json_async(big, context="telemetry big")
    assert len(parsed["temperature_log"]) == 80_000
    # Small payloads still parse correctly (inline path).
    small = await server._safe_json_async('{"a": 1}', context="small")
    assert small == {"a": 1}
    assert await server._safe_json_async("", context="empty") is None
