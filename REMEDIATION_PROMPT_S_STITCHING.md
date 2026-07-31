# REMEDIATION PROMPT S — STITCHING (executable slice of STITCHING_BLUEPRINT.md)

**Audience:** an AI coding agent with LOW capability. Do exactly what each task says, in order, one
task per commit. Do not improvise. Do not skip. If anything does not match, STOP (see §0.2).

**What this prompt covers vs. what it cannot.** The blueprint (`STITCHING_BLUEPRINT.md`) has
software phases (A, B, D-spec, G-tests, H) that CAN be built and tested against this repo right now,
and hardware phases (C provisioning, E firmware, F app-BLE) that CANNOT — they need a physical
ESP32, a BLE radio, and human hardware engineering, so no test in this repo can prove them. This
prompt gives you **verbatim, test-backed tasks for the software slice** and **writes the shared
contracts + failing conformance tests** the hardware work will later satisfy. It does NOT contain
firmware C or BLE Dart code — writing that blind, untested, would be worse than not writing it.
Tasks marked 🔵 HUMAN-GATED are described so a human/hardware engineer can pick them up; you do NOT
execute those, you only create the contract/spec files they point to.

**Repo root:** `C:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`

---

## 0 · READ BEFORE EVERY TASK

### 0.1 Hard rules (breaking any one = STOP and report)
1. **One task per commit.** Never combine two S-tasks in a commit.
2. **Copy code blocks VERBATIM.** Do not rename, reformat, "improve", or add extra code.
3. **Find code by the ANCHOR string given, never by line number.** If an anchor is found **0 times
   or 2+ times**, you are BLOCKED (§0.2) — do not guess which one.
4. **Additive only.** New files, new functions, new endpoints. Never delete, rename, or weaken
   existing code or existing tests. You may edit an existing file ONLY where a task's anchor tells
   you to, and only as shown.
5. **Every code task ships its own test, and you run it before committing.**
6. **No new dependencies.** No `pip install`, no `npm install`, no new package in any manifest.
7. **NEVER read, print, cat, grep, or open `backend/.env`** — it holds a LIVE PRODUCTION database
   URL. `pytest` is safe: `backend/tests/conftest.py` forces an in-memory SQLite database.
8. **NEVER run `alembic`** (no upgrade/downgrade/revision). Not needed anywhere in this prompt.
9. **Do not touch anything a task did not name.** If you notice another bug, write it in NOTES.

### 0.2 BLOCKED protocol
STOP. Run `git status` (do not discard anything). Report exactly:
`TASK id / ANCHOR text / FILE / how many times found / the 3 lines around what you did find`.
Do NOT substitute a different anchor. Do NOT continue to the next task.

### 0.3 Report after every task (paste this filled in)
```
TASK: <id>   STATUS: done | blocked
FILES CHANGED: <exact paths>
TESTS RUN: <command> -> <n passed / n failed>
COMMIT: <sha or "not committed">
NOTES: <=3 lines, or "none"
```

### 0.4 Manifest — tick a box only after that task's test passes
```
S0 : [ ] verify state (no edits)
S1 : [ ] Phase A — reconcile ADR-002 internal contradictions (DOC ONLY)
S2 : [ ] Phase B1 — capability type in apiV2types.ts (frontend)
S3 : [ ] Phase B2 — getBatchCapabilities client fn in api2.ts (frontend) + test
S4 : [ ] Phase D3b — GET /sync-status/{device_id} backend endpoint + test
S5 : [ ] Phase H  — GET /unbound-sessions backend endpoint + test
S6 : [ ] Phase D  — write the BLE sync protocol spec (DOC) + shared test vectors (DATA)
S7 : [ ] Phase G  — Dart canonical-bytes conformance test (TDD, expected-failing until firmware/app impl)
GATE: [ ] backend full suite 0 failed + collected >= baseline ; frontend vitest 0 failed
🔵 HUMAN-GATED (NOT executed here): Phase A crypto decision (A4), Phase C, E, F, I, J, K
```

### 0.5 Commands you will use
```bash
# backend, one test file:
cd backend && python -m pytest tests/<file>.py -q
# backend, collected-count baseline / gate:
cd backend && python -m pytest --collect-only -q 2>/dev/null | grep -c "::"
# backend, full suite (GATE only, ~15 min):
cd backend && python -m pytest -q
# frontend, one test file:
cd portal && npx vitest run src/__tests__/<file>.test.ts
# frontend, all tests (GATE):
cd portal && npx vitest run
```

---

# S0 — VERIFY STATE (NO EDITS)
```bash
cd "C:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv"
git status --short
cd backend && python -m pytest --collect-only -q 2>/dev/null | grep -c "::"   # write this down = BASELINE
```
Then confirm each anchor this prompt depends on exists **exactly once** (report the count for each):
```bash
grep -c 'const TIMELINE_V2 = true;' portal/src/pages/BatchDetail.tsx          # expect 1
grep -c 'export function getBiomassLedger' portal/src/api2.ts                 # expect 1
grep -c 'from sqlalchemy import select, update' backend/routers/telemetry.py  # expect 1
grep -c 'async def bind_session' backend/routers/telemetry.py                 # expect 1
grep -c 'class BurnSession' backend/models.py                                 # expect 1
```
**Done when:** BASELINE recorded and all five counts are 1. **BLOCKED if** any count is not 1.

---

# S1 — PHASE A: reconcile ADR-002's internal contradictions (DOC ONLY)

## Why
`docs/adr-002-edge-transport-and-crypto.md` states two things twice, each time contradicting
itself: (1) §3 step 1 says pairing is pinned to registered units, but A3.3 says no pairing; (2) §2.2
says `seq` is per `(batch_uuid, channel)`, but A1 makes `session_uuid` primary. A later reader will
pick the wrong one. This task records the resolutions **as the blueprint decided** (A0, A5). No code.

## Step 1 — append a reconciliation note at the very end of the file
**ANCHOR (the last line of `docs/adr-002-edge-transport-and-crypto.md`, appears once):**
```
M7 (phone relay) consumes A1/A2 as its server contract.
```
Add directly beneath it:
```

---

# ADDENDUM B — Contradiction reconciliation (2026, post-stitching-review)
Two statements in this ADR contradict later addenda in the same ADR. Resolved here so no reader
picks the superseded version:
- **Pairing:** §3 step 1 ("pairing pinned to the site's registered units") is SUPERSEDED by A3.3.
  Decision: **no BLE pairing/bonding.** The Ed25519 signature is the security boundary, not the
  BLE link. Any phone may courier; the server dedups and verifies.
- **seq scope:** §2.2's "monotonic per (batch_uuid, channel)" is SUPERSEDED by A1. Decision: **seq
  is monotonic per (session_uuid, channel)** — batch_uuid is usually null at write time and cannot
  scope a chain.
- **Producer key storage:** any reading that the Ed25519 key lives in an ATECC608B is WRONG — the
  ATECC608B is NIST P-256 only and cannot do Ed25519. Per §2.1 the key lives in **ESP32-S3
  flash-encrypted NVS + secure boot v2**. (A discrete Ed25519-capable secure element remains an
  open BOM option; see STITCHING_BLUEPRINT.md A4.)
```

## Step 2 — verify + commit
```bash
git add docs/adr-002-edge-transport-and-crypto.md
git commit -m "docs(adr-002): reconcile pairing, seq-scope, and producer-key contradictions"
```
**Done when:** committed. No test (doc-only). **BLOCKED if** the anchor is not found exactly once.

---

# S2 — PHASE B1: capability descriptor TYPE (frontend, additive)

## Why
The backend already serves `GET /api/v1/portal/batches/{uuid}/capabilities`
(`backend/portal/capability_routes.py`) but the frontend has no type or client for it. This task
adds only the TypeScript type. (B2 adds the client function; a later UI task consumes it.)

## Step 1 — add the interface to `portal/src/apiV2types.ts`
**ANCHOR (appears once — the real first line of `portal/src/apiV2types.ts`):**
```typescript
import type { BatchRow } from "./api";
```
Insert the block below **directly ABOVE that anchor line** (an `export interface` sitting above the
file's imports is valid TypeScript). Do NOT modify or delete the anchor line itself. Ignore §0.3's
"appears once" rule for the word `export` here — the file legitimately has several exports; the
anchor above is the unique, correct target.
```typescript
// Capability descriptor — mirrors backend capabilities.resolve_batch_capabilities exactly.
// The portal renders panels from this stated verdict instead of guessing from failed fetches.
export interface BatchCapabilities {
  telemetry: "v2" | "legacy" | "none";
  thermal: boolean;
  load: boolean;
  timeline: boolean;
  journeys: boolean;
  ledgers: boolean;
  provenance_code: boolean;
  tier: "none" | "load" | "thermal" | "full";
}
```
> If `portal/src/apiV2types.ts` does not exist, CREATE it containing exactly the block above and
> nothing else.

## Step 2 — verify it compiles (type-only, no test yet)
```bash
cd portal && npx tsc --noEmit
```
**Done when:** `tsc --noEmit` reports no NEW errors about `apiV2types.ts` (pre-existing errors
elsewhere are not yours — note them, don't fix them). **BLOCKED if** it reports a syntax error in
the block you added.

## Step 3 — commit
```bash
git add portal/src/apiV2types.ts
git commit -m "feat(portal): BatchCapabilities type mirroring the backend descriptor"
```

---

# S3 — PHASE B2: getBatchCapabilities client function (frontend) + test

## Why
Give the portal one typed client call for the descriptor, tested in isolation, following the exact
pattern of the existing functions in `api2.ts`.

## Step 1 — add the client function to `portal/src/api2.ts`
**ANCHOR (appears once):**
```typescript
export function getBiomassLedger(params: {
```
Add this block **directly ABOVE that anchor line** (so the import of the type sits with the other
exports and the function precedes the ledger export):
```typescript
// ── capability descriptor (STITCHING Phase B) ───────────────────────────────
import type { BatchCapabilities } from "./apiV2types";

/** Fetch the per-batch capability verdict. The portal should render panels from
 * this instead of probing endpoints and catching failures. */
export function getBatchCapabilities(uuid: string): Promise<BatchCapabilities> {
  return req(`/api/v1/portal/batches/${uuid}/capabilities`);
}

```
> NOTE: `import` lines are normally at the top of a file. TypeScript/ESM allows this import here and
> the existing bundler handles it, but if `npx tsc --noEmit` in Step 3 complains about an import not
> being at the top, MOVE only the `import type { BatchCapabilities } from "./apiV2types";` line up to
> sit beside the existing `import` lines at the top of `api2.ts` (leave the function where it is).

## Step 2 — create the test `portal/src/__tests__/capabilities.test.ts` (NEW)
```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { getBatchCapabilities } from "../api2";
import { setSession } from "../auth";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const FULL = {
  telemetry: "none",
  thermal: false,
  load: false,
  timeline: true,
  journeys: true,
  ledgers: true,
  provenance_code: false,
  tier: "none",
};

describe("getBatchCapabilities", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("calls the capabilities endpoint for the given batch uuid", async () => {
    setSession("tok-abc", "verifier");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(FULL));

    const caps = await getBatchCapabilities("batch-123");

    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/v1/portal/batches/batch-123/capabilities",
    );
    expect(caps.timeline).toBe(true);
    expect(caps.tier).toBe("none");
  });

  it("returns every declared capability key", async () => {
    setSession("tok-abc", "verifier");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(FULL));
    const caps = await getBatchCapabilities("b1");
    for (const key of [
      "telemetry", "thermal", "load", "timeline",
      "journeys", "ledgers", "provenance_code", "tier",
    ]) {
      expect(caps).toHaveProperty(key);
    }
  });
});
```

## Step 3 — verify + commit
```bash
cd portal && npx tsc --noEmit          # no new errors from api2.ts / the test
cd portal && npx vitest run src/__tests__/capabilities.test.ts
git add portal/src/api2.ts portal/src/__tests__/capabilities.test.ts
git commit -m "feat(portal): getBatchCapabilities client fn + isolated test"
```
**BLOCKED if** the test fails on first run — report the failure, do not edit the test to make it
pass.

---

# S4 — PHASE D3b: sync-status watermark endpoint (backend) + test

## Why
A courier phone (or, once firmware exists, any courier) needs to learn what the server has already
stored for a device, so the device can safely reclaim flash — even if the phone that delivered the
data never returns (STITCHING_BLUEPRINT D3b). This is a read of non-secret seq numbers. Endpoint:
`GET /api/v2/telemetry/sync-status/{device_id}` → the max stored `seq` per (session_uuid, channel).

## Step 1 — widen one import in `backend/routers/telemetry.py`
**ANCHOR (appears once):**
```python
from sqlalchemy import select, update
```
Replace with:
```python
from sqlalchemy import func, select, update
```

## Step 2 — append the endpoint at the END of `backend/routers/telemetry.py`
**ANCHOR (the last non-empty lines of the file, appears once):**
```python
    return {
        "status": "ok",
        "points_inserted": points_inserted,
        "skipped_chunks": skipped_chunks,
    }
```
Add directly beneath it:
```python


@router.get("/api/v2/telemetry/sync-status/{device_id}")
async def sync_status(
    device_id: str,
    _user: PortalUser = Depends(require_role()),
    session: AsyncSession = Depends(get_session),
):
    """STITCHING D3b — the confirmed watermark per (session, channel) for a device.

    A courier relays this back to the edge unit so it can reclaim flash for data
    the SERVER already holds, without depending on the specific phone that
    delivered it ever returning. Returns max stored seq per (session, channel);
    chunks with seq=None (legacy/cellular, no chain) are ignored. Never raises on
    an unknown device — an unknown device simply has an empty watermark list.
    """
    rows = (
        await session.execute(
            select(
                TelemetryChunk.session_uuid,
                TelemetryChunk.channel,
                func.max(TelemetryChunk.seq),
            )
            .where(TelemetryChunk.device_id == device_id)
            .where(TelemetryChunk.seq.isnot(None))
            .group_by(TelemetryChunk.session_uuid, TelemetryChunk.channel)
        )
    ).all()
    return {
        "device_id": device_id,
        "watermarks": [
            {"session_uuid": s, "channel": c, "max_seq": int(m)}
            for (s, c, m) in rows
        ],
    }
```

## Step 3 — create the test `backend/tests/test_sync_status.py` (NEW)
```python
"""S4 / STITCHING D3b — sync-status returns the max stored seq per (session, channel)."""
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from models import PortalUser, TelemetryChunk
from portal.auth import hash_password

pytestmark = pytest.mark.asyncio

DEVICE = "edge-sync-1"


@pytest_asyncio.fixture
async def auth(client, session_factory):
    async with session_factory() as s:
        s.add(PortalUser(
            email="sync@x.org", password_hash=hash_password("pw-123456789"), role="admin",
        ))
        await s.commit()
    token = (await client.post(
        "/api/v1/portal/login",
        json={"email": "sync@x.org", "password": "pw-123456789"},
    )).json()["token"]
    return {"Authorization": f"Bearer {token}"}


def _chunk(seq, channel="T1", session="sess-1"):
    return TelemetryChunk(
        batch_uuid=None,
        device_id=DEVICE,
        channel=channel,
        t_start=datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc),
        t_end=datetime(2026, 7, 23, 9, 10, tzinfo=timezone.utc),
        sample_period_s=10.0,
        session_uuid=session,
        seq=seq,
        prev_hash=None,
        payload_json='{"values":[400.0]}',
        signature="sig-" + uuid.uuid4().hex[:8],
    )


async def test_watermark_is_max_seq_per_channel(client, session_factory, auth):
    async with session_factory() as s:
        s.add(_chunk(0)); s.add(_chunk(1)); s.add(_chunk(2))
        s.add(_chunk(0, channel="T2"))
        await s.commit()
    r = await client.get(f"/api/v2/telemetry/sync-status/{DEVICE}", headers=auth)
    assert r.status_code == 200, r.text
    marks = {(w["session_uuid"], w["channel"]): w["max_seq"] for w in r.json()["watermarks"]}
    assert marks[("sess-1", "T1")] == 2
    assert marks[("sess-1", "T2")] == 0


async def test_unknown_device_is_empty_not_error(client, auth):
    r = await client.get("/api/v2/telemetry/sync-status/does-not-exist", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"device_id": "does-not-exist", "watermarks": []}


async def test_seqless_chunks_ignored(client, session_factory, auth):
    async with session_factory() as s:
        s.add(_chunk(None, session="sess-legacy"))
        await s.commit()
    r = await client.get(f"/api/v2/telemetry/sync-status/{DEVICE}", headers=auth)
    assert all(w["session_uuid"] != "sess-legacy" for w in r.json()["watermarks"])
```

## Step 4 — verify + commit
```bash
cd backend && python -m pytest tests/test_sync_status.py -q
git add backend/routers/telemetry.py backend/tests/test_sync_status.py
git commit -m "feat(telemetry): sync-status watermark endpoint (STITCHING D3b)"
```
**BLOCKED if** any test fails first run — report it, do not weaken the test.

---

# S5 — PHASE H: unbound-sessions listing endpoint (backend) + test

## Why
`bind_session` already exists but an admin has no way to FIND the sessions that need binding
(STITCHING_BLUEPRINT Phase H). Endpoint: `GET /api/v2/telemetry/unbound-sessions` → burn sessions
with no batch, oldest first, with a chunk count so the admin can see which are real.
> NOTE (H0, do NOT try to fix here): auto-proposing WHICH batch a session belongs to needs a
> device→kiln→batch link that does not exist yet. This task only LISTS unbound sessions; it does not
> propose matches. Record that limitation in NOTES.

## Step 1 — append the endpoint at the END of `backend/routers/telemetry.py`
**ANCHOR (appears once — the end of the sync_status function you added in S4):**
```python
        "watermarks": [
            {"session_uuid": s, "channel": c, "max_seq": int(m)}
            for (s, c, m) in rows
        ],
    }
```
Add directly beneath it:
```python


@router.get("/api/v2/telemetry/unbound-sessions")
async def unbound_sessions(
    _user: PortalUser = Depends(require_role("admin")),
    session: AsyncSession = Depends(get_session),
):
    """STITCHING Phase H — burn sessions with no batch yet, oldest first, each with
    its chunk count. An admin binds these via the existing bind_session endpoint.
    Does NOT propose a batch (that needs a device->kiln->batch link that does not
    exist yet — H0). Empty list, never an error, when nothing is unbound.
    """
    counts = dict(
        (
            await session.execute(
                select(TelemetryChunk.session_uuid, func.count(TelemetryChunk.id))
                .group_by(TelemetryChunk.session_uuid)
            )
        ).all()
    )
    sessions = (
        await session.execute(
            select(BurnSession)
            .where(BurnSession.batch_uuid.is_(None))
            .order_by(BurnSession.started_at.asc())
        )
    ).scalars().all()
    return {
        "unbound_sessions": [
            {
                "session_uuid": bs.session_uuid,
                "device_id": bs.device_id,
                "started_at": bs.started_at.isoformat() if bs.started_at else None,
                "chunk_count": int(counts.get(bs.session_uuid, 0)),
            }
            for bs in sessions
        ]
    }
```

## Step 2 — create the test `backend/tests/test_unbound_sessions.py` (NEW)
```python
"""S5 / STITCHING Phase H — list burn sessions that still need a batch bound."""
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio

from models import PortalUser, BurnSession, TelemetryChunk
from portal.auth import hash_password

pytestmark = pytest.mark.asyncio

T0 = datetime(2026, 7, 23, 9, 0, tzinfo=timezone.utc)


@pytest_asyncio.fixture
async def auth(client, session_factory):
    async with session_factory() as s:
        s.add(PortalUser(
            email="unbound@x.org", password_hash=hash_password("pw-123456789"), role="admin",
        ))
        await s.commit()
    token = (await client.post(
        "/api/v1/portal/login",
        json={"email": "unbound@x.org", "password": "pw-123456789"},
    )).json()["token"]
    return {"Authorization": f"Bearer {token}"}


async def test_lists_only_unbound_oldest_first(client, session_factory, auth):
    async with session_factory() as s:
        s.add(BurnSession(session_uuid="s-late", device_id="d1", started_at=T0 + timedelta(hours=2)))
        s.add(BurnSession(session_uuid="s-early", device_id="d1", started_at=T0))
        s.add(BurnSession(
            session_uuid="s-bound", device_id="d1", started_at=T0 + timedelta(hours=1),
            batch_uuid="already-bound",
        ))
        await s.commit()
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    assert r.status_code == 200, r.text
    ids = [x["session_uuid"] for x in r.json()["unbound_sessions"]]
    assert ids == ["s-early", "s-late"]          # oldest first, bound one excluded


async def test_chunk_count_reported(client, session_factory, auth):
    async with session_factory() as s:
        s.add(BurnSession(session_uuid="s-cc", device_id="d1", started_at=T0))
        for _ in range(3):
            s.add(TelemetryChunk(
                batch_uuid=None, device_id="d1", channel="T1", t_start=T0, t_end=T0,
                sample_period_s=10.0, session_uuid="s-cc", seq=None, prev_hash=None,
                payload_json='{"values":[1.0]}', signature="sig-" + uuid.uuid4().hex[:8],
            ))
        await s.commit()
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    row = [x for x in r.json()["unbound_sessions"] if x["session_uuid"] == "s-cc"][0]
    assert row["chunk_count"] == 3


async def test_empty_when_nothing_unbound(client, auth):
    r = await client.get("/api/v2/telemetry/unbound-sessions", headers=auth)
    assert r.status_code == 200
    assert r.json() == {"unbound_sessions": []}
```

## Step 3 — verify + commit
```bash
cd backend && python -m pytest tests/test_unbound_sessions.py -q
git add backend/routers/telemetry.py backend/tests/test_unbound_sessions.py
git commit -m "feat(telemetry): unbound-sessions listing endpoint (STITCHING Phase H)"
```
**BLOCKED if** any test fails first run.

---

# S6 — PHASE D: BLE sync protocol spec (DOC) + shared test vectors (DATA)

## Why
The firmware and the app must implement the SAME wire protocol. Write it down once so both build
against one document (STITCHING_BLUEPRINT Phase D). This is the single biggest integration risk —
an unwritten protocol means two guesses that meet wrong. No code is executed here; you create the
spec and a machine-checkable vectors file.

## Step 1 — create `docs/ble-sync-protocol.md` (NEW) with EXACTLY this content
```markdown
# BLE Store-and-Forward Sync Protocol (STITCHING Phase D)

The single wire contract both the ESP32 firmware (Phase E) and the phone app (Phase F) implement.
Neither side may deviate; a change here is a change to both, in the same PR, with the vectors below
regenerated.

## Transport
- One GATT service, two characteristics: `TX` (device -> phone, notify) and `RX` (phone -> device,
  write). Nordic-UART-style byte stream. No other characteristics carry protocol data.
- No pairing/bonding (ADR-002 A3.3 / Addendum B). Filter by advertised device_id. The Ed25519
  signature is the security boundary.

## Framing
Every logical message is length-prefixed and split to fit the negotiated MTU:
`{ msg_type: u8, chunk_id: u32, packet_index: u16, total_packets: u16, payload: bytes }`.
The receiver reassembles by `chunk_id` and verifies the reassembled length before acting.

## Message types
| msg_type | name | direction | payload |
|---|---|---|---|
| 1 | ChunkRequest | phone -> device | `{channel, from_seq?}` (omit from_seq = oldest unsynced) |
| 2 | ChunkData | device -> phone | one signed envelope (the exact JSON the backend ingests) |
| 3 | SyncAck | phone -> device | `{channel, synced_through_seq}` — server-CONFIRMED, not BLE-received |
| 4 | SyncNack | phone -> device | `{channel, seq, reason}` — permanently rejected (e.g. 422), stop offering |
| 5 | TimeSync | phone -> device | `{utc_ms}` — first action every connection |
| 6 | Health | device -> phone | `{unsynced_bytes, flash_full, fw_version}` |

## Advertising
- Advertise the sync service when there is unsynced data (include device_id + unsynced-byte-count).
- ALSO advertise on a slow interval (~every few minutes) when idle, so a phone can TimeSync and read
  Health on a drifting-but-quiet unit (STITCHING D2a). A 16-byte device_id may exceed the 31-byte
  legacy advert budget — use BLE 5 extended advertising or a scan response.

## Eviction safety (the point of the ack cycle)
1. Phone sends ChunkRequest. 2. Device streams ChunkData oldest-first. 3. Phone relays each envelope
to `/api/v2/telemetry/ingest` via its OFFLINE OUTBOX (not live pass-through). 4. Only after the
SERVER confirms (200 ok/duplicate) does the phone send SyncAck. 5. Device marks flash reclaimable
ONLY on SyncAck — never on BLE transfer completing.
- **Retention floor:** never evict anything younger than 90 days regardless of any ack (guards
  against a spoofed unauthenticated SyncAck — STITCHING D3a). Evictable = synced-AND-older-than-90d.
- **Any courier** can carry the watermark from `GET /api/v2/telemetry/sync-status/{device_id}`, not
  only the phone that delivered the data (STITCHING D3b).

## Signed envelope (what ChunkData carries)
The envelope and its canonical signing bytes are defined by `backend/tools/golden_vectors.json` —
that file is the authority. Firmware and app MUST reproduce `canonical_hex` for every vector byte
for byte. See STITCHING Phase G.

## FLOAT PRECISION INVARIANT (contract-level, load-bearing)
Every float a producer emits (`values[]`, `sample_period_s`) MUST carry exactly 1 decimal place. The
edge firmware guarantees this by rounding each 10 s bucket to 1 dp (`aggregate.c`); that is what lets
Python `json.dumps`, C `%.1f`, and Dart `toStringAsFixed(1)` produce identical bytes. A producer that
emits more precision (e.g. `412.25`) would sign bytes the 1-dp implementations cannot reproduce —
never do so without changing all three canonicalizers together in the same PR and regenerating the
golden vectors.
```

## Step 2 — create the shared vectors pointer `docs/ble-sync-vectors.json` (NEW)
This is a machine-readable copy-pointer so both implementations test against one artifact:
```json
{
  "canonical_authority": "backend/tools/golden_vectors.json",
  "note": "Firmware (C) and app (Dart) must reproduce canonical_hex for every vector in the authority file byte-for-byte before either is trusted. Do not hand-edit; regenerate the authority with: cd backend && python tools/gen_golden_vectors.py",
  "protocol_spec": "docs/ble-sync-protocol.md"
}
```

## Step 3 — commit (no test — these are contract documents)
```bash
git add docs/ble-sync-protocol.md docs/ble-sync-vectors.json
git commit -m "docs(ble): store-and-forward sync protocol spec + shared vectors pointer (STITCHING Phase D)"
```
**Done when:** both files exist and committed.

---

# S7 — PHASE G: Dart canonical-bytes conformance test (TDD, expected-failing)

## Why
The app (and later the firmware) must sign the EXACT bytes the backend verifies. Write the test
FIRST (test-driven): it loads the committed golden vectors and asserts a Dart canonicalizer
reproduces them. Until someone writes the Dart canonicalizer (Phase F / a human), this test FAILS —
that is correct and intended; it is the executable definition of "done" for that future work.

> This task CREATES the failing test and a clearly-marked stub it targets. You do NOT implement the
> real canonicalizer (that pairs with the app-BLE work, Phase F). Mark the test skipped so it does
> not break CI, with a comment saying to un-skip it when the canonicalizer lands.

## Step 1 — copy the vectors where a Dart test can read them
```bash
cp backend/tools/golden_vectors.json test/golden_vectors.json
```
> If `backend/tools/golden_vectors.json` does not exist, STOP — run
> `cd backend && python tools/gen_golden_vectors.py` first (that is an R5 deliverable), then retry.

## Step 2 — create the stub `lib/services/telemetry_canonical.dart` (NEW)
```dart
/// STITCHING Phase G — canonical signing bytes for a telemetry envelope.
///
/// MUST byte-match backend TelemetryChunkIn.canonical_bytes():
///   - keys sorted alphabetically
///   - compact separators (no spaces): , and :
///   - the producer_signature field EXCLUDED from the signed bytes
///   - UTF-8
///
/// NOT YET IMPLEMENTED. This throws on purpose so the conformance test in
/// test/telemetry_canonical_test.dart fails until a real implementation lands
/// (pairs with the app-courier work, STITCHING Phase F). Do not fake it.
library;

String canonicalJson(Map<String, dynamic> envelope) {
  throw UnimplementedError(
    'canonicalJson not implemented — see STITCHING Phase F/G',
  );
}
```

## Step 3 — create the test `test/telemetry_canonical_test.dart` (NEW)
```dart
import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:dmrv_app/services/telemetry_canonical.dart';

void main() {
  // Un-skip this group when canonicalJson is implemented (STITCHING Phase F).
  group('telemetry canonical bytes match backend golden vectors', skip: 'canonicalizer not implemented yet (STITCHING Phase F)', () {
    test('every committed vector reproduces byte-for-byte', () {
      final file = File('test/golden_vectors.json');
      final vectors = jsonDecode(file.readAsStringSync()) as List<dynamic>;
      expect(vectors, isNotEmpty);
      for (final v in vectors) {
        final envelope = Map<String, dynamic>.from(v['envelope'] as Map);
        final expectedHex = v['canonical_hex'] as String;
        final actualHex =
            utf8.encode(canonicalJson(envelope)).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
        expect(actualHex, expectedHex, reason: 'canonical bytes drifted for $envelope');
      }
    });
  });
}
```
> The package name in the import (`package:dmrv_app/...`) must match `name:` in `pubspec.yaml`. If it
> differs, change ONLY that import line to the real package name (grep `^name:` in `pubspec.yaml`).

## Step 4 — verify the test is collectable and SKIPPED (not failing, not passing)
```bash
flutter test test/telemetry_canonical_test.dart
```
Expected: the test is reported as **skipped**, and the run is green. (If `flutter` is not installed
in this environment, that is fine — note it in NOTES and still commit; the file is the deliverable.)

## Step 5 — commit
```bash
git add test/golden_vectors.json lib/services/telemetry_canonical.dart test/telemetry_canonical_test.dart
git commit -m "test(telemetry): TDD Dart canonical-bytes conformance stub, skipped until impl (STITCHING Phase G)"
```

---

# GATE — after S1–S7 committed

```bash
# backend
cd backend && python -m pytest -q                                             # expect 0 failed
cd backend && python -m pytest --collect-only -q 2>/dev/null | grep -c "::"   # expect >= BASELINE + 6
# frontend
cd portal && npx vitest run                                                   # expect 0 failed
```
Report:
```
GATE RESULT
backend:  <n> passed, <n> failed
collected: <n>  (baseline <n>, expected +6: 3 sync-status + 3 unbound-sessions ... note if your count differs)
frontend: <n> passed, <n> failed
manifest: S0 S1 S2 S3 S4 S5 S6 S7 -> <done/blocked each>
```
**BLOCKED if** backend failed > 0, OR the collected count DROPPED below baseline (you deleted a
test), OR frontend failed > 0.

---

# 🔵 HUMAN-GATED — DO NOT EXECUTE (recorded so nothing is lost)

These are in `STITCHING_BLUEPRINT.md` and CANNOT be done by an agent against this repo — they need
hardware, a BLE radio, or a human decision. Do not attempt, do not fake. Listed so the human owner
knows they are the remaining work:

- **A4 — producer-key crypto decision.** ESP32-S3 encrypted NVS (recommended) vs an Ed25519 secure
  element vs backend P-256. A human/architect call; blocks all firmware signing.
- **Phase C — device provisioning firmware + app flow** (needs hardware).
- **Phase E — ESP32 firmware** (sampling, flash log, chain, signing, GATT server; needs hardware +
  the physical enclosure/power decisions E9/E11).
- **Phase F — app-side BLE courier** (drain/relay/ack; needs a device to talk to; when built, it
  implements `canonicalJson` from S7 and un-skips that test).
- **Phase I — dual-run parity + `telemetry_v2` canary** (needs real field data first).
- **Phase J — observability, rate limiting, key-rotation runbook, load tests** (ops, pre second org).
- **Phase K — LOAD channel** (parked; needs a product decision on what it changes in credit math).

## Final reminders
- ❌ Never invent firmware C or BLE Dart in this prompt — untested hardware code is worse than none.
- ❌ Never weaken a test to make it green. A red test is a finding, not a chore.
- ❌ Never read `backend/.env`. Never run `alembic`.
- ✅ Reality disagrees with this document → **BLOCKED**, every time.
```
