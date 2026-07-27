# dMRV Evolution — Agent Execution Plan (M0–M6, atomic tasks, no-break)

**Audience:** AI coding agents executing ONE task at a time.
**Parent doc:** `DMRV_EVOLUTION_BLUEPRINT.md` (the architecture & why). This file is the HOW — small tasks, verbatim code, tests for everything.
**Prime directive:** if a code block is given, copy it VERBATIM. If reality differs from what a task claims, STOP → BLOCKED protocol. Never improvise a substitute.

---

## 0 · GLOBAL RULES (re-read before EVERY task)

### 0.1 Hard rules
1. **Frozen files:** `portal/src/api.ts`, `portal/src/auth.ts`, `portal/src/compliance.ts`, `portal/src/qr.ts` are NEVER edited. New portal API calls go in the NEW file `portal/src/api2.ts` (created in M2.6). Backend `/api/v1/*` response shapes are frozen — new shapes live under `/api/v2/*` or new `/api/v1/portal/...` ADDITIVE endpoints only.
2. **No-break law (expand-migrate-contract):** every schema change is ADDITIVE first (nullable columns, new tables). Dual-write before switching reads. Contract (drop/rename) only in M6, never earlier. Every Alembic migration must have a working `downgrade()`.
3. **No god files:** new backend module ≤ ~300 lines; new router = its own file in `backend/routers/` or `backend/portal/`; new portal component = own folder `src/ui/<Name>/` or `src/components/<Name>/` with `.tsx` + `.module.css` + `.test.tsx`. If a task would push a file past the limit, STOP → the task is mis-scoped → BLOCKED.
4. **Every task ships its test.** Backend: `backend/tests/test_<module>.py` (pytest, follow existing fixtures in `backend/tests/conftest.py` — READ it first). Portal: vitest colocated `.test.tsx`. Never weaken an existing assertion.
5. **Anchor targeting:** find code by anchor strings given in the task, never by line number. Anchor found 0 or 2+ times → BLOCKED.
6. **No new heavy dependencies.** Postgres partitioning ≠ TimescaleDB. SSE ≠ websocket lib (FastAPI `StreamingResponse` + portal `EventSource`). Charts = hand-built SVG per existing `TemperatureChart` pattern. Leaflet already exists. If you think you need a new package → BLOCKED (exception: none in this plan).
7. **Tokens only** in portal CSS (see `portal/audit/REMEDIATION_BLUEPRINT.md` §0 — same rules apply).
8. **Feature flags:** every user-visible new capability is gated on an `AppConfig` key (pattern in task M0.2), default OFF, enabled per-org.
9. **Signatures are sacred:** any new device-write endpoint takes `device_id: str = Depends(verify_signature)` exactly like `backend/routers/evidence.py`. No unsigned ingest path, ever — this is the moat (blueprint §6.5).
10. **THE GRACEFUL-DEGRADATION LAW (nothing rigid):** sensors are OPTIONAL ENHANCERS, never requirements. The signed mobile-app evidence path (photos, app-captured readings, manual weights) remains a first-class, fully-credit-eligible path FOREVER. Every feature in this plan must work at every sensor tier:
    - **Tier 0 — none:** app evidence only (today's flow, untouched). All compliance gates satisfiable exactly as they are now.
    - **Tier L — load only:** load cells stream `LOAD`; temperatures stay app-evidenced.
    - **Tier T — thermal only:** thermocouples stream `T1..T4`; weights stay app/scale-evidenced.
    - **Tier F — full:** all channels.
    Tiers are **per kiln, mixed freely within one site/org**, and are *derived from what actually streams* — never a hard configuration wall. NO gate, endpoint, chart, timeline, or export may fail, block, or nag because a channel is absent. Sensor data, when present, upgrades evidence richness; its absence changes nothing about eligibility. Any task that would violate this → BLOCKED.

### 0.2 BLOCKED protocol
1. STOP; revert this task's partial edits. 2. Report `STATUS: blocked` + anchor/file searched + first 3 lines actually found. 3. Do NOT substitute, do NOT skip ahead.

### 0.3 Commands
- Backend task: `cd backend && python -m pytest tests/<your test file> -q` then full `python -m pytest -q` at phase gate.
- Portal task: `cd portal && npx vitest run <file> && npx tsc --noEmit`; phase gate `npm run verify`.
- Migration task additionally: `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` against a scratch SQLite file (READ `backend/alembic/env.py` first; the repo pattern supports it).

### 0.4 Report format (mandatory)
```
TASK: <id>  STATUS: done|blocked
FILES: <paths>
TESTS: <files> → <pass>/<total>   VERIFY: pytest/tsc → clean|<n> errors
NOTES: <≤3 lines>
```

### 0.5 Task manifest (tick as you go)
```
M0: [x]0.1 [x]0.2 [x]0.3
M1: [x]1.1 [x]1.2 [x]1.3  [x]1.4 [x]1.5      # 1.3 UNBLOCKED via ADR-001 B (ff98f42)
M2: [x]2.1 [x]2.2 [x]2.3 [x]2.4 [x]2.5 [x]2.6 [x]2.7 [x]2.8 [x]2.9  # 2.3/2.4 landed (portal/telemetry_routes.py, handoff accepted); chart stitch landed (77c281a); M2.9 sessions/courier landed
M3: [ ]3.1 [ ]3.2 [ ]3.3
M4: [ ]4.1 [ ]4.2 [ ]4.3 [ ]4.4
M5: [ ]5.1 [ ]5.2
M6: [ ]6.1 [ ]6.2 [ ]6.3
```

---

## 0.6 · ARCHITECTURAL DECISIONS LOCKED BY INDEPENDENT AUDIT (do not re-litigate; do not "improve")
| # | Decision | Why (one line) |
|---|---|---|
| A1 | SSE auth = single-use 60 s tickets, never bearer-in-URL | `EventSource` cannot send Authorization headers; tokens in URLs leak into logs |
| A2 | `telemetry_points` composite PK + conflict-ignoring inserts | ORM requires a PK; duplicates become free idempotency instead of errors |
| A3 | Batch codes: NULL-until-lineage-known; seq per (kiln, day); slot derived from IST hour | Unique codes are permanent — junk placeholders would be wrong forever |
| A4 | Credit bridge: uniform 10 s resample, gaps excluded (conservative), probe-max semantics | Sensor gaps may only SHORTEN a sustained-temperature window, never lengthen eligibility |
| A5 | Reject only future `t_start` (> now+300 s); old chunks always accepted | 72 h offline ring-buffer backfill is normal operation, not an anomaly |
| A6 | Chart series colors from `chartPalette.indigoTone` only | verde/ember are semantic status tokens — the portal audit's own rule |
| A7 | Manual-distance journeys can never lower the LCA transport deduction; GPS-traced can | Typed numbers must not be able to increase credits — registry defensibility |
| A8 | Pub/sub + tickets live in `telemetry_bus.py`, unit-tested; SSE endpoints get smoke tests only | Weak agents drown in SSE integration tests; the bus IS the logic |
| — | Scope note: NO Flutter/mobile changes in M0–M6 | Tier-0 path is untouched; edge units talk directly to the ingest API |

---

# PHASE M0 — FOUNDATIONS

## M0.1 Read-and-map (no edits — produces a NOTES report only)
READ, in order: `backend/models.py` (entity map), `backend/routers/evidence.py` (signature pattern), `backend/portal/routes.py` (portal endpoint pattern), `backend/tests/conftest.py` (test fixtures/app factory), `backend/alembic/versions/b7c1d2e3f4a5_portal_users_org_scoping.py` (migration pattern), `backend/db.py`, `backend/credit_engine.py` (anchor: `temperature_readings`). Report in NOTES: (a) how tests get a DB session, (b) how migrations name/structure upgrade/downgrade, (c) the exact function + line-anchor where the credit engine reads telemetry. **Done when:** report delivered. This report is pasted into every later backend task's context.

## M0.2 Feature-flag helper
**File (NEW):** `backend/feature_flags.py` (≤60 lines):
```python
"""Per-org feature flags on top of AppConfig — additive, default OFF.

Key format: "ff.<flag>.<org_id>" or global "ff.<flag>".  Values "on"/"off".
Never cache across requests — flags must be flippable live.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import AppConfig

FLAGS = ("telemetry_v2", "hierarchy_v2", "timeline_v2", "journeys_v2", "ledgers_v2")


async def flag_enabled(session: AsyncSession, flag: str, org_id: str | None = None) -> bool:
    if flag not in FLAGS:
        raise ValueError(f"unknown feature flag: {flag}")
    keys = [f"ff.{flag}"] + ([f"ff.{flag}.{org_id}"] if org_id else [])
    rows = (
        await session.execute(select(AppConfig).where(AppConfig.key.in_(keys)))
    ).scalars().all()
    by_key = {r.key: (r.value or "").strip().lower() for r in rows}
    for key in reversed(keys):  # org-specific beats global
        if key in by_key:
            return by_key[key] == "on"
    return False
```
CAVEAT: READ `models.py` anchor `class AppConfig` first — if its columns are not `key`/`value`, adapt attribute names to the real ones and say so in NOTES (this is the ONE permitted adaptation).
**Test (NEW):** `backend/tests/test_feature_flags.py` — 4 cases: unknown flag raises; default off; global on; org override beats global.

## M0.3 Staging replay harness
**File (NEW):** `backend/tools/replay_seed.py` — script that runs `seed_demo_rich.py` against a scratch DB then asserts: batch count > 0, every batch has `lca_signature`, `/api/v1/portal/summary` responds via TestClient. Used as the phase-gate smoke test.
**Test:** the script IS the test; wire a thin `backend/tests/test_replay_smoke.py` that imports and runs its `main()` under pytest marker `slow`.

**M0 GATE:** full pytest green.

---

# PHASE M1 — IDENTITY & HIERARCHY (all additive)

## M1.1 Schema: networks + site/kiln/batch extensions
**File (NEW):** Alembic migration `backend/alembic/versions/<rev>_hierarchy_v2.py` following the repo migration pattern. Upgrade (SQLAlchemy `op.` calls, not raw SQL, matching repo style):
- new table `networks`: `network_id VARCHAR(64) PK`, `org_id VARCHAR(128) NULL index`, `name VARCHAR(255) NOT NULL`, `country_code VARCHAR(4) NULL`, `created_at TIMESTAMPTZ default now`.
- `facilities` add: `network_id VARCHAR(64) NULL index`, `site_code VARCHAR(16) NULL`.
- `kilns` add: `site_id VARCHAR(64) NULL index` (stores `facility_uuid`), `kiln_code VARCHAR(16) NULL`, `sensor_profile VARCHAR(16) NOT NULL DEFAULT 'none'` (whitelist `none|load_only|thermal_only|full` — a DECLARED expectation used only for display labels like Circonomy's "(IoT)/(Non-IoT)" and ops dashboards; the *actual* tier is always derived from what streams — Global Rule 10. `DEFAULT 'none'` means every existing and future kiln works with zero setup).
- `batches` add: `batch_code VARCHAR(40) NULL UNIQUE index`, `network_id VARCHAR(64) NULL index`, `site_id VARCHAR(64) NULL index`.
Downgrade drops exactly these. **DO NOT** touch any existing column.
**Model edits:** `backend/models.py` — add `class Network(Base)` + the new mapped columns on existing classes, copying the exact `mapped_column` style used by anchor `network_id` examples… (READ neighboring classes; match style precisely).
**Test (NEW):** `backend/tests/test_hierarchy_schema.py` — create Network, Facility w/ network_id, Kiln w/ site_id + each `sensor_profile` value (invalid value rejected), Batch w/ batch_code; assert round-trip + uniqueness of batch_code + default profile is `none`.

## M1.2 Batch-code generator (pure function, zero I/O)
**File (NEW):** `backend/batch_codes.py` (≤80 lines) — copy VERBATIM:
```python
"""Human-readable provenance batch codes (display identity — UUID stays king).

Format:  {CC}{org:02d}{network}P{site:02d}S{slot}K{kiln:02d}B{DDMMYY}{seq:02d}
Example: IN01A001P03S2K07B23072601
Deterministic; collision-safe via the per-day sequence. NEVER used as a key,
NEVER parsed to recover facts — the DB columns are the truth, the code is a
human handle.
"""
import re
from datetime import datetime

_NETWORK_RE = re.compile(r"^[A-Z]\d{3}$")


def make_batch_code(
    *,
    country: str,
    org_num: int,
    network_code: str,
    site_num: int,
    slot_num: int,
    kiln_num: int,
    day: datetime,
    seq: int,
) -> str:
    if not (len(country) == 2 and country.isalpha()):
        raise ValueError("country must be 2 letters")
    if not _NETWORK_RE.match(network_code):
        raise ValueError("network_code must match ^[A-Z]\\d{3}$, e.g. A001")
    if not (0 <= org_num <= 99):
        raise ValueError("org_num out of range 0..99")
    if not (0 <= site_num <= 99):
        raise ValueError("site_num out of range 0..99")
    if not (0 <= slot_num <= 9):
        raise ValueError("slot_num out of range 0..9")
    if not (0 <= kiln_num <= 99):
        raise ValueError("kiln_num out of range 0..99")
    if not (1 <= seq <= 99):
        raise ValueError("seq out of range 1..99")
    return (
        f"{country.upper()}{org_num:02d}{network_code}"
        f"P{site_num:02d}S{slot_num}K{kiln_num:02d}"
        f"B{day:%d%m%y}{seq:02d}"
    )
```
**Slot derivation (Batch has no slot column — audit A3):** add to the same file `slot_for(received_at_ist: datetime) -> int` — hour < 12 → 1 (morning), < 17 → 2 (afternoon), else 3 (evening). Convert to IST (+05:30) before bucketing; document that slot is a derived convenience, not a recorded fact.
**Test (NEW):** `backend/tests/test_batch_codes.py` — golden case `("IN",1,"A001",3,2,7,2026-07-23,1) == "IN01A001P03S2K07B23072601"`, validation raises ×4, slot buckets ×3 (incl. an IST-boundary case).

## M1.3 Backfill script (dry-run first)
**File (NEW):** `backend/tools/backfill_batch_codes.py` — iterates batches WHERE `batch_code IS NULL` **whose kiln→site→network lineage is fully mapped. Unknown lineage → LEAVE `batch_code` NULL** (portal already falls back to short-UUID). NEVER write placeholder codes (audit A3: codes are UNIQUE and permanent — a junk `X000P00` code written today is wrong forever once the real hierarchy is assigned; NULL costs nothing and heals itself on the next run). Sequence: scoped **per (kiln, day)**, ordered by `received_at, id`. `--dry-run` prints first 20 without writing. Idempotent (skips non-null); safe to re-run weekly as ops maps more history.
**Test:** `backend/tests/test_backfill_batch_codes.py` — 3 same-kiln same-day batches → seq 01,02,03; second kiln same day restarts at 01; unmapped-lineage batch stays NULL; re-run → zero changes.

## M1.4 Expose hierarchy + code in portal list (additive fields only)
**File:** `backend/portal/routes.py` — anchor the batches list serializer (READ it; find where `batch_uuid`/`status` dict is built). ADD keys `batch_code`, `network_id`, `site_id` (nullable) to the response dict. Adding keys to a JSON object is non-breaking; **removing/renaming is forbidden**.
**Portal:** `portal/src/pages/Batches.tsx` — Batch column cell: show `batch_code ?? shortId(uuid)` with `.mono`; the type for the extra fields comes from `api2.ts` (M2.6) — until then read via `(b as any).batch_code ?? null` is FORBIDDEN; instead add interface `BatchRowV2 extends BatchRow` in a NEW file `portal/src/apiV2types.ts` and cast at the page boundary once, with a comment.
**Tests:** backend `test_portal_read.py` — extend existing list test to assert new keys present+nullable; portal Batches.test updated (code renders when present).

## M1.5 Cascading filters (flagged)
Behind `hierarchy_v2` flag: new endpoint `GET /api/v1/portal/hierarchy` returns `{networks:[{network_id,name,sites:[{site_id,name,kilns:[...]}]}]}` (own router file `backend/portal/hierarchy_routes.py`, registered in `app_factory.py` after anchor `portal_issuance_router`). Portal `FilterBar` gains optional cascading selects fed by it (render only when data non-empty).
**Tests:** backend endpoint test (empty DB → empty list; seeded → nested shape); portal FilterBar test (selects hidden when no data).

**M1 GATE:** full pytest + `npm run verify` + replay harness green.

---

# PHASE M2 — TELEMETRY PLANE (the new subsystem)

## M2.1 Schema: chunks + points
Migration `_telemetry_v2.py`:
- `telemetry_chunks`: `id BIGINT PK autoincr`, `batch_uuid VARCHAR(36) NOT NULL index`, `device_id VARCHAR(255) NOT NULL`, `channel VARCHAR(16) NOT NULL`, `t_start/t_end TIMESTAMPTZ NOT NULL`, `sample_period_s REAL NOT NULL`, `payload_json TEXT NOT NULL`, `signature VARCHAR(128) NOT NULL`, `received_at TIMESTAMPTZ default now`, **UNIQUE(batch_uuid, channel, t_start, signature)** ← idempotent re-ingest (edge retries are free).
- `telemetry_points`: `batch_uuid VARCHAR(36) NOT NULL`, `channel VARCHAR(16) NOT NULL`, `ts TIMESTAMPTZ NOT NULL`, `value REAL NOT NULL`, **composite PRIMARY KEY (batch_uuid, channel, ts)** — SQLAlchemy ORM requires a PK, and this one doubles as point-level idempotency. Plain table on SQLite; on Postgres additionally partitioned (audit A2).
- **Inserts are conflict-ignoring** — helper in `backend/telemetry_store.py` (NEW, ≤60 lines), copy VERBATIM:
```python
"""Dialect-aware idempotent point inserts (audit A2). Duplicate (batch,
channel, ts) rows are silently skipped — chunk retries and overlapping
re-aggregations are free, never errors."""
from sqlalchemy.ext.asyncio import AsyncSession

from models import TelemetryPoint


async def insert_points(session: AsyncSession, rows: list[dict]) -> int:
    if not rows:
        return 0
    dialect = session.bind.dialect.name
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    stmt = insert(TelemetryPoint).values(rows).on_conflict_do_nothing(
        index_elements=["batch_uuid", "channel", "ts"]
    )
    result = await session.execute(stmt)
    return result.rowcount or 0
```
**Models:** add `TelemetryChunk`, `TelemetryPoint` to `models.py` (match style; TelemetryPoint maps the composite PK via three `mapped_column(..., primary_key=True)`).
**Test:** `test_telemetry_schema.py` — insert chunk+points; duplicate chunk rejected (IntegrityError); duplicate POINTS silently skipped (insert_points returns 0 second time); round-trip.

## M2.2 Ingest endpoint (signed, idempotent, additive)
**File (NEW):** `backend/routers/telemetry.py` (own router; register in `app_factory.py`):
```python
"""/api/v2/telemetry — signed edge-telemetry ingest (blueprint §4.1).

Chunk body (exactly what the device signs):
{
  "batch_uuid": "...", "channel": "T1",          # T1|T2|T3|T4|LOAD
  "t_start": "...Z", "sample_period_s": 10.0,
  "values": [412.5, 418.0, ...]                   # ≤ 720 per chunk (2 h @10 s)
}
"""
```
Endpoint `POST /api/v2/telemetry/ingest`, `device_id: str = Depends(verify_signature)` (import exactly as `routers/evidence.py` does). Validation: channel whitelist; `1 <= len(values) <= 720`; batch exists; values finite; `sample_period_s in [1, 60]`; **clock rule (audit A5): reject 422 only when `t_start > now + 300s` (the future is impossible) — `t_end` far in the PAST is NORMAL (72 h offline ring-buffer backfill) and must never be rejected or warned.** Behavior: insert chunk (on unique-violation → return `{"status": "duplicate"}` 200 — idempotency, not error); unpack values via `telemetry_store.insert_points` (ts = t_start + i·period); compute `t_end`. Returns `{"status":"ok","points":N}`.
**DO NOT** touch `PyrolysisTelemetry` or the credit engine in this task.
**Test:** `test_telemetry_ingest.py` — signed happy path (reuse the signing helper existing device tests use — READ `tests/test_*device*` for the fixture); duplicate chunk → `duplicate`, points not doubled; bad channel 422; unsigned 401/403; oversize values 422.

## M2.3 Read API + rollup
**File:** same router. `GET /api/v1/portal/batches/{uuid}/telemetry2?channels=T1,T2,T3,T4,LOAD&res=10s|1m` (portal-auth via the same dependency `portal/routes.py` uses — READ its auth Depends and copy). Response:
```json
{"channels": {"T1": {"points": [[ts, v], ...], "max": 477.3, "min": 88.0}},
 "burn": {"t_start": "...", "t_end": "...", "gaps": [["ts1","ts2"]]}}
```
`res=1m` averages in SQL (GROUP BY minute bucket). **Gaps are computed and returned, never interpolated** (moat §6: absence is evidence).
**Rollup job:** `backend/tools/rollup_telemetry.py` — nightly 1-minute rollup into `telemetry_rollup_1m` (same shape as points + `agg VARCHAR(8)`); table added in this task's small migration.
**Test:** ingest 2 channels → read both res; gap detection (two chunks with a hole → one gap reported); rollup job produces expected bucket means.

## M2.4 Live SSE stream (ticket-authenticated — audit A1)
**Why tickets:** the browser `EventSource` API CANNOT send an Authorization header — bearer-auth on the stream endpoint would 401 every real client. Never put the session token in a query string (logs). The pattern:
1. `POST /api/v1/portal/streams/burn/{uuid}/ticket` — normal portal bearer auth → `{"ticket": "<32-byte urlsafe token>", "expires_in": 60}`. Ticket stored in an in-module dict `{ticket: (batch_uuid, expiry)}`, SINGLE-USE (popped on redemption).
2. `GET /api/v1/portal/streams/burn/{uuid}?ticket=…` — validates+consumes the ticket (401 if missing/expired/wrong-batch), then `StreamingResponse(media_type="text/event-stream")`, yields `event: telemetry\ndata: {json}\n\n` per new ingest; heartbeat `: ping\n\n` every 20 s.
**Structure (audit A8 — testability):** the pub/sub lives in its own module `backend/telemetry_bus.py` (NEW, ≤80 lines): `subscribe(batch_uuid) -> asyncio.Queue`, `unsubscribe(...)`, `publish(batch_uuid, payload)`, plus the ticket mint/redeem functions — pure asyncio, zero FastAPI imports. Module docstring carries verbatim: "Single-process pub/sub. Correct for the current single-worker uvicorn deployment (see Dockerfile CMD); swap the internals for Redis pub/sub when workers > 1 — the interface stays."
**Tests:** unit-test `telemetry_bus` thoroughly (publish→queue receives; unsubscribe cleans; ticket single-use; ticket expiry; wrong-batch rejected). The HTTP endpoints get ONE smoke test each (ticket mint 200 + stream 401-without-ticket); do NOT attempt a full SSE integration test — if you find yourself fighting TestClient streaming, the bus tests are the required coverage, note it and move on.

## M2.5 Credit-engine bridge (zero-touch shim — conservative by construction, audit A4)
**File (NEW):** `backend/telemetry_bridge.py`: `async def temperature_array_for(session, batch_uuid) -> list[float] | None`. EXACT semantics (do not deviate):
0-A. **⚠⚠ BURN WINDOW — MANDATORY (ADR-001 §A3, read `docs/adr-001-thermal-and-identity.md` before coding this task).** Continuous sensors record ramp-up and cool-down; legacy app readings do not. Building the array from the FULL recording drives `min(readings)` to ambient and can push the ≥50 % sustain fraction under threshold — i.e. instrumented kilns would fail where app-evidenced kilns pass, violating Global Rule 10. Therefore:
```
burn_start := first ts where max(T1,T2,T3) >= 350.0
burn_end   := last  ts where max(T1,T2,T3) >= 350.0
compliance_array := 10 s buckets of max(T1,T2,T3) within [burn_start, burn_end], gaps excluded
```
Fewer than 60 surviving buckets → return None (no claim), never a fabricated pass. Full history stays stored/charted; only the COMPLIANCE view is windowed. Required tests: (a) **parity** — instrumented batch vs equivalent legacy batch → identical verdict; (b) **ramp-up/cool-down** — a full-history batch must not fail where its hot-phase-only twin passes.

0-B. **DECISION GATE (ADR-001 §A2, DECIDED): the compliance gate is MIN/fraction-based** (`corroboration.py: PYROLYSIS_MIN_C = 350.0`, `derive_min_temp`, ≥60 samples) — so which probes feed the array directly changes credit eligibility. Module MUST start with `COMPLIANCE_CHANNELS: tuple[str, ...] = ("T1", "T2", "T3")  # ADR-001 A2 — T4 (base) is context only` and use ONLY those channels (T4 still stored/charted). **This is now DECIDED, not open:** Kon-Tiki literature confirms the zone below the pyrolysis front legitimately cools to 150–450 °C, so a base probe in a min/fraction test would fail compliant batches. The only item still awaiting a methodology initial is the *aggregation choice* (`max(T1..T3)` vs a single nominated probe — ADR-001 §A6); that gates enabling `telemetry_v2` in PRODUCTION, not this task.
1. Load points for `COMPLIANCE_CHANNELS` only, **resample onto a uniform 10 s grid** (bucket = floor(ts/10s); bucket value = MAX across those probes and samples in the bucket — hottest-point semantics; with a MIN-over-time gate this is the lenient intra-bucket choice, acceptable because bucket width is 10 s, but do not widen buckets).
2. **Gaps produce NO entries** — a missing bucket is absent from the array, never interpolated, never zero-filled. This is deliberately CONSERVATIVE: the C3 sustained-duration logic counts array entries, so sensor gaps can only shorten the sustained window, never lengthen it. A gap can therefore never make a batch MORE eligible.
3. Return None when zero T-channel points exist.
**Org resolution for the flag (Batch has no org_id):** `org = project.org_id if batch.project_id and project else None` (READ how `portal/routes.py` resolves batch→project; copy). None → global flag only.
**File:** `backend/credit_engine.py` — at the anchor found in M0.1 where `temperature_readings` is read from the telemetry payload, ADD (not replace): if legacy array missing/empty AND `flag_enabled(session, "telemetry_v2", org)` → use bridge array. The legacy path stays first. ONE conditional, ≤10 lines, comment referencing this task id.
**Test:** `test_telemetry_bridge.py` — streamed batch + flag on → C3 identical to equivalent legacy batch; flag off → unchanged (provisional reason present); **gap case: stream with a 30-min hole → sustained-duration strictly shorter than the gapless equivalent (assert conservativeness)**; mixed sample periods resample correctly.

## M2.6 Portal client v2 (new file — api.ts stays frozen)
**File (NEW):** `portal/src/api2.ts` (≤140 lines): typed `getTelemetry2(uuid, params)`, `openBurnStream(uuid, onChunk): Promise<() => void>` — implements the TICKET flow (audit A1): first `POST …/streams/burn/{uuid}/ticket` via the authed fetch helper, then `new EventSource(url + "?ticket=" + ticket)` (tickets are single-use + 60 s TTL, so URL exposure is harmless); returns a disposer that closes the EventSource. Auto-reconnect: on `error` event, mint a fresh ticket and reopen, max 3 attempts with 2 s backoff, then call `onChunk` with `{type:"stream_closed"}` so the chart can show a quiet "live view ended" note. Plus `HierarchyResponse` fetch (M1.5) and a minimal `req()` re-implementation (do NOT import private internals from api.ts; duplicate the 20-line fetch helper with the same AuthError semantics — comment why).
**Test:** `api2.test.ts` — mocks fetch; AuthError on 401; ticket minted before EventSource opens; disposer closes; reconnect mints a NEW ticket (jsdom EventSource stub).

## M2.7 ThermalMapChart (the Circonomy-parity chart, done better)
**Files (NEW):** `portal/src/ui/ThermalMapChart/` (tsx+css+test). Hand-built SVG (extend the geometry lessons of `TemperatureChart` — `preserveAspectRatio="none"`, y padded [8,192]):
- Up to 4 series colored from the EXISTING dashboard convention `portal/src/config/chartPalette.ts` — `indigoTone(0..3)` for T1–T4 (READ that file first; audit A6: verde/ember are SEMANTIC tokens, never chart-series colors — our own portal audit rule). 2px lines, direct end-labels, NO legend box.
- **MAX badge** top-right chip: `MAX {v}°C` — `.mono`; **turns `--status-success-fg` when ≥450°C sustained gate passes** (prop `gateSatisfied: boolean`) — the compliance tie-in Circonomy lacks (blueprint §6.2).
- Gap segments rendered as literal breaks + a `.micro` "sensor gap" annotation (never interpolate).
- Live mode: accepts `stream?: boolean`; appends points from `openBurnStream`; respects `prefers-reduced-motion` (no slide animation, just redraw).
- **Tier-aware (Global Rule 10):** renders exactly the channels present — 1 thermocouple renders 1 line, 4 render 4; ZERO channels → the component returns null (parent falls back to the legacy app-evidence chart). Never renders placeholder/empty series, never shows "sensor missing" warnings — absence of sensors is a normal tier, not an error.
**Test:** fixture 4-channel data → 4 polylines, max badge value, gap break count; gate prop toggles badge class; 1-channel fixture → 1 polyline; empty channels → renders null.

## M2.8 LoadTelemetryChart + BatchDetail wiring (flagged)
**Files (NEW):** `portal/src/ui/LoadTelemetryChart/` — step-after path, load-event dots, chips row (`BIOMASS`, `BIOCHAR`, `LAST LOAD` — mono/tabular); returns null when no `LOAD` channel (Global Rule 10). **File:** `portal/src/pages/BatchDetail.tsx` — inside the existing "Burn telemetry" Card, render per-tier: thermal channels present → ThermalMapChart; `LOAD` present → LoadTelemetryChart; **any mix works independently** (load-only kilns show only the weight curve beside the legacy temperature display; thermal-only show only the map); nothing present → legacy `TemperatureChart` exactly as today. All paths coexist — a Tier-0 batch renders pixel-identical to the current release.
**Test:** BatchDetail test — full fixture renders both charts; load-only fixture renders LoadTelemetryChart + legacy temp; thermal-only renders map only; Tier-0/legacy fixture renders old chart identically; no v2 fetch crash when endpoint 404s (graceful).

**M2 GATE:** full pytest + verify + replay; manual: seeded batch streams live in portal.
**M2h (hardware, parallel — human+agent):** write `docs/edge-firmware-contract.md` from M2.2's docstring (chunk JSON + HMAC canonicalization + provisioning via `EnrollmentToken` — READ `routers/devices.py` for the enrollment flow first). Agent task = the doc; humans build the 2 pilot units.

---

# PHASE M3 — STAGE TIMELINE

## M3.1 Schema + projection
Migration `_stage_events.py`: `batch_stage_events`: `id PK`, `batch_uuid index`, `stage VARCHAR(32)` (whitelist: `sourcing,moisture,loading,firing,biochar_addition,pre_quenching,quenching,yield,mixing,packaging,dispatch,application,lab`), `started_at/ended_at TIMESTAMPTZ NULL`, `source VARCHAR(16)` (`device|edge|projected|admin`), UNIQUE(batch_uuid, stage).
**File (NEW):** `backend/stage_projection.py` — pure function `project_stages(batch, media, telemetry, dispatches, applications) -> list[StageEvent]` deriving stages for historical batches (firing from telemetry t_start/t_end or burn timestamps in the legacy payload; quenching/moisture from capture_type timestamps; application from EndUseApplication; missing → NO row — absence stays absent).
**Backfill:** `backend/tools/backfill_stages.py` (idempotent, `--dry-run`).
**Tests:** projection unit tests (rich batch → expected stages; sparse batch → sparse rows; never fabricates), schema round-trip, backfill idempotency.

## M3.2 Timeline endpoint
`backend/portal/timeline_routes.py`: `GET /api/v1/portal/batches/{uuid}/timeline` → ordered stage list, each: `{stage, started_at, ended_at, state: done|active|empty, media: [MediaItem-shaped…], telemetry_summary?: {max_temp, duration_min}}`. Empty stages ARE returned with `state:"empty"` (blueprint §6.4) and — **better than Circonomy** — when an empty stage matches a `provisional_reasons` entry, include `blocking: true` so the UI can show WHY absence matters.
**Test:** seeded batch → full ordered response; stage-less batch → all-empty timeline; blocking flag appears when reason present.

## M3.3 Portal timeline UI (flagged `timeline_v2`)
**Files (NEW):** `portal/src/components/StageTimeline/` — vertical spine (existing `VerificationChain` visual language: markers/connectors from tokens), per-stage: title, mono timestamps (`fmtDateTime`), media thumbnails (reuse `EvidenceGallery` cell — import its exported pieces; if not exported, extract `MediaCell` into its own component first — that extraction is part of this task, with its own test), empty state (`—  no {stage} records` + `StatusPill warning "blocking"` when `blocking`).
`BatchDetail.tsx`: render StageTimeline above EvidenceGallery when flag on + timeline non-empty; the old grouped gallery remains below (both, not either — verifiers keep the familiar view).
**Test:** timeline renders stages in order; empty+blocking states; legacy batches (404 timeline) → no crash, gallery only.

**M3 GATE:** full suites green.

---

# PHASE M4 — DISTRIBUTION INTELLIGENCE

## M4.1 Schema
Migration `_journeys_v2.py`: `dispatch_journeys` (`dispatch_uuid` FK-unique, `distance_km REAL NULL`, `vehicle_reg VARCHAR(32) NULL`, `fuel_type VARCHAR(16) NULL` whitelist `diesel|petrol|ev|bullock|none`, `emissions_kg REAL NULL`, `factor_version VARCHAR(16) NULL`, `route_geojson TEXT NULL`); `dispatch_manifest_lines` (`dispatch_uuid index`, `container VARCHAR(32)`, `count INT`, `unit_kg REAL NULL`, `volume_l REAL NULL`, `product VARCHAR(64)`); `facilities`/`dispatch_sites` add `contact_name/contact_phone VARCHAR NULL` (phone stored masked-at-rest? NO — stored raw, MASKED at the portal serializer like farmers' PII — READ `portal/routes.py` farmer masking anchor and copy the approach).
## M4.2 Emissions factors (versioned, like LCA constants)
**File (NEW):** `backend/emissions_factors.py` — `FACTORS_V1 = {"diesel_truck_5t_kg_per_km": 0.82, "tractor_diesel_kg_per_km": 0.75, ...}` with docstring citing source `[VERIFY factors with founders before production]`; `estimate_emissions(distance_km, fuel_type, vehicle_class) -> (kg, factor_version)`. Pure, unit-tested.
## M4.3 Journey endpoints + LCA hook (flag `journeys_v2`)
Device-signed `POST /api/v2/dispatch/{uuid}/journey` (edge/app GPS trace or manual distance; body carries `distance_source: "gps"|"manual"`) + portal read (additive keys on the existing dispatch list serializer + `GET .../journey`). LCA hook mirrors M2.5's shim pattern with the **registry-conservativeness rule (audit A7): a measured journey may LOWER the transport deduction below the conservative default ONLY when `distance_source == "gps"` (evidence-backed). `manual` journeys apply `max(measured_deduction, default_deduction)` — typed numbers can never increase credits.** Anchor the transport constant in `credit_engine.py`/`lca` module (M0.1 report), ONE guarded conditional.
**Tests:** endpoint auth/validation; emissions math golden cases; LCA parity flag off/on; **conservativeness: manual journey with tiny distance → deduction unchanged; gps journey with tiny distance → deduction reduced.**
## M4.4 Portal: journey panel + route map + manifest
**Files (NEW):** `portal/src/components/JourneyPanel/` — journey metrics rows (mono), manifest table, masked contact, application-evidence status chip (linkage: count of EndUseApplication rows for the dispatch's batch); route polyline via existing Leaflet (`ParcelMap` patterns — extract shared `MapCanvas` if ParcelMap isn't reusable as-is; extraction = own subtask+test). Wire into `Dispatch.tsx` as a detail side-panel (Farmers-style select → panel, WITH scroll-into-view — don't repeat audit finding F1).
**Tests:** panel renders all sections; masked phone (`••••1234`); empty journey → em-dashes, never fabricated values.

**M4 GATE:** suites green + one seeded dispatch shows full journey panel.

---

# PHASE M5 — LEDGERS & ANALYTICS

## M5.1 Biomass ledger endpoint (flag `ledgers_v2`)
`backend/portal/ledger_routes.py`: `GET /api/v1/portal/ledgers/biomass?from&to&bucket=day|month&site_id&network_id` → rows (date, site, network, species, kg, batch_codes[], media thumb refs) + aggregates (total_kg, by_species). Source: batches + moisture/sourcing evidence (READ what field holds intake mass — `biomass_input_kg` on Batch). Cursor-paginated like existing lists.
## M5.2 Portal ledger page
**Files (NEW):** `portal/src/pages/Ledger.tsx` + route `/ledger` + sidebar entry (icon `Scale` or `Sheet` from lucide, size 16): FilterBar presets `MTD|YTD|Custom` (date inputs), DataTable (species chips via StatusPill-inert, kg right/tabular, batch_code chips linking to detail), StatBand aggregates. Every convention from the portal audit applies (tokens, em-dash, sentence case).
**Tests:** endpoint bucket math golden cases; page renders rows/aggregates; presets set correct query params.

**M5 GATE:** suites green.

---

# PHASE M6 — CONTRACT & HARDEN

## M6.1 Legacy telemetry read-path retirement — ONLY when every open batch has v2 data: credit engine reads bridge first, legacy array second (flip the M2.5 conditional order); `PyrolysisTelemetry` stays forever as the signed historical record (never dropped).
## M6.2 Perf pass: `EXPLAIN` the telemetry read + ledger queries at 100k-batch synthetic scale (`backend/tools/synth_scale_seed.py` NEW — generates without the credit pipeline, clearly marked synthetic); budgets: telemetry read p95 < 300 ms @ 1m res, ledger < 500 ms. Add missing indexes via migration if budgets fail.
## M6.3 Docs + flag default-on proposal: update `DMRV_EVOLUTION_BLUEPRINT.md` status table; produce `EVOLUTION_RESULT.md` (manifest ticks, test counts, perf numbers, screenshots of the two new charts + timeline + journey panel).

---

## DEPENDENCY GRAPH
```
M0 → M1 → M2 (M2h parallel) → M3 → M6
              M2.6 → M2.7/M2.8
M1 → M4 → M6        M1 → M5 → M6
Portal tasks within a phase are parallel-safe unless they touch the same page file.
```

## MODULARITY GUARANTEES (the "nothing rigid" contract — verify at every phase gate)
1. **A customer with zero hardware onboards in one day:** enroll devices (phones) → app evidence → full credit eligibility. No sensor purchase, no config, no degraded experience — this is today's flow and it is protected by regression tests, not intentions.
2. **A customer with ONLY load cells** gets the weight curve + mass-balance chips; temperature stays app-evidenced; every gate, export, and timeline works. Same for thermal-only.
3. **Tiers are per KILN, not per company** — one site can run 3 full-IoT kilns beside 20 bare ones; lists show the mix (profile label per kiln), batches from both flow through identical pipelines.
4. **Upgrading a kiln = bolting on sensors + enrolling the edge unit.** No migration, no downtime, no data model change — the next burn simply has more channels. Downgrading (sensor breaks mid-season) is equally silent: the burn completes on app evidence.
5. **Sensor data never punishes:** a gap, a dead thermocouple, or a missing channel can never make a batch LESS eligible than a Tier-0 batch with the same app evidence. Richness is a bonus lane, not a toll gate.
6. Timeline (M3), journeys (M4), and ledgers (M5) all source from whichever evidence exists — projection functions take every input as optional.

## THINK-0.1% ADDITIONS BAKED IN (vs. blind Circonomy copy)
1. Signed telemetry chunks (they trust; we prove) — M2.1/M2.2.
2. Idempotent ingest via unique(batch,channel,t_start,signature) — retries free — M2.1.
3. Gaps as first-class data + "sensor gap" annotations (never interpolate) — M2.3/M2.7.
4. Compliance-aware charts (MAX badge goes semantic on the ≥450 °C gate) — M2.7.
5. Empty timeline stages that carry `blocking: true` from provisional_reasons — M3.2.
6. Journey emissions that FEED the LCA deduction, not just a label — M4.3.
7. PII masking discipline extended to dispatch contacts — M4.1.
8. Everything org-flagged for gradual rollout; SQLite-dev/Postgres-prod parity preserved — M0.2/M2.1.
```
