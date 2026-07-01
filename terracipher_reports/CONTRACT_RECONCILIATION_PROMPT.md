# Contract Reconciliation — Remediation Prompt (Phase 7‑R)

**For the engineer/agent implementing the fix.** This document is written to be executed
**without guessing**. Every claim below is grounded in a real file and line. Before you change
anything, you re‑verify the "current state" snippet exists *verbatim*; if it does not, **STOP** and
re‑read — the code drifted and the rest of the plan may be stale.

> **Goal in one sentence:** the credit‑bearing inputs (`wet_yield_kg`, `min_recorded_temp_c`,
> `transport_distance_km`) must be **derived server‑side from corroborating evidence streams**, never
> required from the batch payload — because at batch‑creation time they do not yet exist — and the
> batch must be marked **PROVISIONAL** (never issued) until each is corroborated.

---

## 0. Anti‑hallucination protocol (read first, obey throughout)

1. **Verify before you edit.** For every task, run the listed `grep`/`Read` first and confirm the
   "Current state" block matches byte‑for‑byte. If it differs, stop and report — do not "fix from
   memory."
2. **Do not invent identifiers.** Field names, column names, and function signatures are enumerated
   in §2 and §3. Use *only* those. If you need one that is not listed, it does not exist — stop.
3. **Canonical field names are a closed set** (§2). The client is the source of truth for wire field
   names (it ships on devices and cannot be hot‑fixed); the server and tests are what get changed to
   match it. Never "fix" a mismatch by changing the client's wire keys.
4. **No new behavior beyond this spec.** Do not add endpoints, auth changes, or schema fields not
   listed. Out‑of‑scope items are in §7 — leave them alone and log them, don't fix them.
5. **One task = one gate.** After each task run its gate. Do not start the next task on a red gate.
6. **The acceptance gate is `backend/tests/test_client_contract.py` going green** with its `xfail`
   markers removed (§6). That file already exists and currently `xfail`s; it is the spec made
   executable.
7. **Determinism:** `ruff format` at the end of every task. Signed/audited JSON keeps `sort_keys=True`.

---

## 1. The problem (verified analysis)

The remediation hardened the backend against a payload contract **the real Flutter client does not
produce**, and verified it with a suite that **mocks out the database layer**. Four root causes:

### 1.1 Workflow is sequential; credit inputs don't exist at batch time
The device writes records at different lifecycle stages (separate Dart outbox writers, each its own
sync):
| Stage | Writer (lib/) | Endpoint | Produces |
|---|---|---|---|
| Harvest | `app_database.dart::insertBiomassSourcingWithOutbox` | `/api/v1/batches` | the batch row |
| Burn | `pyrolysis_writer.dart::insertPyrolysisTelemetryWithOutbox` | `/api/v1/telemetry` | temperature log → **min temp** |
| Post‑burn | `yield_end_use_writers.dart::insertYieldMetricsWithOutbox` | `/api/v1/yield` | **wet yield kg** |
| Field application | `yield_end_use_writers.dart::insertEndUseWithOutbox` | `/api/v1/application` | GPS → **transport km** |

So `wet_yield_kg`, `min_recorded_temp_c`, `transport_distance_km` are **created after the batch**.
Requiring them on `/batches` (Phase 7) is temporally impossible, not merely a schema mismatch.

### 1.2 CONTRACT‑A — `/batches` rejects every real batch (CRITICAL)
`BatchPayload` (`backend/server.py:185‑252`) deliberately accepts the client's `biomass_sourcing`
fields, **but Phase 7 added three `required` fields the client never sends:**
- `backend/server.py:206` `wet_yield_kg: float = Field(..., gt=0.0, ...)`
- `backend/server.py:207‑209` `min_recorded_temp_c: float = Field(..., ge=-50.0, le=1500.0, ...)`
- `backend/server.py:210‑215` `transport_distance_km: float = Field(..., ge=0.0, le=20000.0, ...)`

Result: real `/batches` POST → **422**. Pinned by
`test_client_contract.py::test_real_client_batch_payload_is_accepted` (xfail).

### 1.3 CONTRACT‑B — telemetry key mismatch (CRITICAL)
- Client sends `temperature_readings` (snake): `lib/data/local/pyrolysis_writer.dart:130`.
- Server reads `temperatureReadingsJson` (camel): `backend/server.py:496`.
- Same bug for attestation: client sends `hw_attestation` (`pyrolysis_writer.dart:132`); server reads
  `hwAttestationJson` (`backend/server.py:506`).

In production the burn‑temperature anti‑fraud gate never sees real readings. Pinned by
`test_client_contract.py::test_telemetry_temperature_key_agreement` (xfail).

### 1.4 CONTRACT‑C — `wet_yield_kg` is never derived; Phase 7 *weakened* the model
`create_batch` already derives min‑temp from telemetry (`server.py:488‑520`) and cross‑checks
transport from application GPS (`server.py:556‑570`), but it takes `wet_yield_kg` **straight from the
client payload** (`server.py:577`, `:608`) — there is no `/yield` corroboration at all. Phase 7's
"require the field" approach replaced *derive‑from‑evidence* with *trust‑the‑client‑number*, which is
strictly weaker for a money‑minting system.

### 1.5 Test integrity — the suite mocks the DB (HIGH)
`backend/tests/conftest.py:163‑204` is an **autouse** fixture that monkeypatches
`AsyncSession.execute` for the whole suite to return a fake
`{"temperatureReadingsJson": [650.0]*60}` for any telemetry query. This is why CONTRACT‑B survived
nine phases: the tests verify the mock (in the server's wrong key), not the code.

---

## 2. Canonical field contract (the closed set — use ONLY these)

**Telemetry** (`/api/v1/telemetry`) — keys the client sends; server MUST read the same:
`telemetry_uuid, batch_uuid, kiln_gross_capacity, burn_start_timestamp, burn_end_timestamp,
min_temp, max_temp, temperature_readings (List[float]), smoke_evidence (List[{stage,sha256}]),
hw_attestation (List[str])`

**Yield** (`/api/v1/yield`):
`yield_uuid, batch_uuid, quench_methodology, gross_volume, wet_yield_weight_kg, dry_yield_weight_kg`
→ corroborated wet yield = `wet_yield_weight_kg`.

**Metadata** (`/api/v1/metadata`):
`batch_uuid, artisan_id, device_hardware_mac, app_build_version, sync_status, created_at`

**Application** (`/api/v1/application`):
`application_uuid, batch_uuid, application_methodology, application_rate_tonnes,
transport_distance_km, latitude, longitude, farmer_photo_path, farmer_photo_sha256`
→ corroborated transport = haversine(batch GPS, application GPS).

**Batch** (`/api/v1/batches`) — what the client actually sends (do not require anything else):
`sourcing_uuid, batch_uuid, feedstock_species, harvest_timestamp, moisture_percent,
moisture_compliant, photo_path, sha256_hash, latitude, longitude, mock_location_enabled,
harvest_uptime_seconds, azimuth, pitch, roll` (+ optional `lab_h_corg`).

**Known fixed signatures (do not change arg order):**
- `haversine_km(lon1, lat1, lon2, lat2) -> float` (see `server.py:533`).
- `calculate_carbon_credit(wet_yield_kg, moisture_percent, min_recorded_temp_c=0.0,
  transport_distance_km=0.0, feedstock_species="Lantana_camara", h_corg_ratio=None) -> LCAAudit`
  (`backend/lca_engine.py:218‑225`); `LCAAudit.provisional: bool` exists (`lca_engine.py:95`).
- `Batch` already has columns `wet_yield_kg, min_recorded_temp_c, transport_distance_km, provisional,
  net_credit_t_co2e` (Phases 7‑8). Reuse them; do not rename.

---

## 3. Target architecture (modular — NOT a bigger `create_batch`)

`create_batch` is already ~180 lines and does idempotency, telemetry, teleport, transport, LCA,
persistence, anchoring. **Do not add more branches to it.** Extract the corroboration logic into a
small, pure, unit‑testable module and a thin shared writer.

### 3.1 New file `backend/corroboration.py` — pure functions, no DB, no FastAPI
```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class Corroboration:
    wet_yield_kg: float | None
    min_recorded_temp_c: float | None
    transport_distance_km: float | None
    provisional: bool
    reasons: list[str] = field(default_factory=list)

def derive_min_temp(telemetry_payload: dict | None) -> tuple[float | None, str | None]:
    """Return (min_temp, reason_if_missing). Reads the CANONICAL 'temperature_readings'.
    Requires >= 60 samples to count as corroborated (existing CSI rule, server.py:497)."""
    if not telemetry_payload:
        return None, "no_telemetry"
    readings = telemetry_payload.get("temperature_readings", [])
    if len(readings) < 60:
        return None, "insufficient_temperature_samples"
    return float(min(readings)), None

def derive_wet_yield(yield_payload: dict | None) -> tuple[float | None, str | None]:
    if not yield_payload:
        return None, "no_yield_record"
    v = yield_payload.get("wet_yield_weight_kg")
    if v is None or float(v) <= 0.0:
        return None, "invalid_wet_yield"
    return float(v), None

def derive_transport_km(
    batch_lat, batch_lon, app_payload: dict | None, *, haversine
) -> tuple[float | None, str | None]:
    if not app_payload or batch_lat is None or batch_lon is None:
        return None, "no_application_record"
    a_lat, a_lon = app_payload.get("latitude"), app_payload.get("longitude")
    if a_lat is None or a_lon is None:
        return None, "application_missing_gps"
    return float(haversine(a_lon, a_lat, batch_lon, batch_lat)), None

def assemble(wet_yield, min_temp, transport, *, has_lab_hcorg: bool) -> Corroboration:
    reasons: list[str] = []
    if wet_yield is None: reasons.append("wet_yield_uncorroborated")
    if min_temp is None: reasons.append("min_temp_uncorroborated")
    if transport is None: reasons.append("transport_uncorroborated")
    if not has_lab_hcorg: reasons.append("assumed_h_corg")
    return Corroboration(wet_yield, min_temp, transport, provisional=bool(reasons), reasons=reasons)
```
These are **pure** → they get their own unit test file `backend/tests/test_corroboration.py`
(table‑driven: each missing input flips `provisional` and lists the right reason).

### 3.2 New helper in `server.py` (thin DB glue, ONE place) `recompute_batch_credit`
A single async function that: loads the telemetry/yield/application rows for a batch, calls the pure
derivers + `assemble`, then `calculate_carbon_credit` with the corroborated (or conservative‑zero)
inputs, and writes `batch.wet_yield_kg / min_recorded_temp_c / transport_distance_km /
net_credit_t_co2e / provisional`. Returns nothing; caller commits.

Call it from **all four** write paths so credit converges as evidence arrives:
`create_batch`, `create_telemetry`, `create_yield`, `create_application`. This replaces the ad‑hoc
recompute already living in `create_application` (`server.py:924‑942`) — delete that and call the
shared helper instead (DRY).

> If a corroborated input is missing, pass a conservative value to `calculate_carbon_credit`
> (`wet_yield`: skip credit / store `None`; `min_temp`: `0.0`; `transport`: `0.0`) **and keep
> `provisional=True`**. A provisional batch's `net_credit_t_co2e` is an estimate, never issuable.

---

## 4. Tasks (sequenced; each has Verify → Change → Gate)

### Task 1 — Make the three LCA fields optional on `BatchPayload`
**Verify:** `grep -n "wet_yield_kg: float = Field(\.\.\." backend/server.py` → line 206.
**Change (`server.py:206‑215`):**
- `wet_yield_kg: float = Field(..., gt=0.0, ...)` → `wet_yield_kg: Optional[float] = Field(None, gt=0.0, ...)`
- `min_recorded_temp_c: float = Field(..., ...)` → `Optional[float] = Field(None, ...)`
- `transport_distance_km: float = Field(..., ...)` → `Optional[float] = Field(None, ...)`
**Also remove** the now‑obsolete payload‑temp validator `_validate_burn_compliance`
(`server.py:238‑250`) — min‑temp is derived in Task 3, not asserted on the payload. (Confirm no other
code references it.)
**Gate:** `python -c "import server"` clean (with env shims, see REMEDIATION_LOG Phase 2);
`pytest -q tests/test_client_contract.py::test_real_client_batch_payload_is_accepted` should now stop
422‑ing on the missing‑field ground (it may still differ on credit — that's Task 3).

### Task 2 — Fix the telemetry consumption keys (CONTRACT‑B)
**Verify:** `grep -n "temperatureReadingsJson\|hwAttestationJson" backend/server.py` → 496, 506.
**Change:** `tel_data.get("temperatureReadingsJson", [])` → `tel_data.get("temperature_readings", [])`
and `tel_data.get("hwAttestationJson")` → `tel_data.get("hw_attestation")`. (This logic moves into
`derive_min_temp` in Task 3; if you do Task 3 first, apply the snake keys there and delete these lines.)
**Gate:** `grep -c "temperatureReadingsJson" backend/server.py` → 0.

### Task 3 — Add `backend/corroboration.py` + `recompute_batch_credit`; refactor `create_batch`
Implement §3.1 and §3.2. In `create_batch`, **replace** the inline telemetry block
(`server.py:487‑520`), the transport cross‑check (`:556‑570`), and the direct‑from‑payload LCA call
(`:572‑583`, `:608‑610`) with a single `await recompute_batch_credit(session, batch, payload)`.
Keep idempotency (`:462‑485`), teleport (`:522‑552`), persistence (`:591‑673`), and anchoring
(`:651‑660`) **unchanged**.
**Gate:** `pytest -q tests/test_corroboration.py` (new unit tests) green;
`pytest -q tests/test_client_contract.py` — both tests **xpass**, then remove the two `xfail` markers
so they are plain green (strict xfail will fail on xpass, forcing this).

### Task 4 — Wire evidence endpoints to recompute
In `create_telemetry`, `create_yield`, `create_application` (`server.py:838‑949`), after persisting
the row, load the batch and `await recompute_batch_credit(...)`. Delete the bespoke recompute in
`create_application` (`:924‑942`).
**Gate:** an integration test (new, `tests/test_corroboration_flow.py`): create batch (provisional,
no credit) → POST telemetry → POST yield → POST application → assert `provisional` flips to the
expected state and `net_credit_t_co2e` reflects corroborated inputs. Use `DISABLE_TELEMETRY_MOCK=1`.

### Task 5 — Remove the global DB mock from conftest (HIGH)
**Verify:** `grep -n "mock_execute\|AsyncSession.execute" backend/tests/conftest.py` → ~179‑200.
**Change:** delete the `legacy_test_environment` `execute` monkeypatch (keep the device‑seeding part).
Migrate any test that depended on the fake telemetry to insert a **real** `PyrolysisTelemetry` row
with `temperature_readings` (snake). This is the largest blast radius — do it last, fix fallout test
by test, never by weakening an assertion.
**Gate:** full `pytest -q` — see §6.

---

## 5. Affected existing tests (disclose + migrate; do NOT weaken assertions)
Expect these to need updates as a *direct consequence* of the fix (verify each before/after):
- `tests/remediation/test_stub_persistence.py` — sends extra/foreign fields (`some_data`, `yield_kg`,
  `field_id`) and asserts full‑dict persistence; update to canonical fields (§2).
- `tests/remediation/test_temperature_log_verification.py` — sends `temperatureReadingsJson`; change to
  `temperature_readings`. Its `missing_qualifying_telemetry_log` 400 expectation
  (`test_single_sample_temp_rejected`) changes: no telemetry now → **provisional**, not 400. Re‑assert
  on `provisional`/credit, keeping the anti‑fraud intent (a `<100 °C` single sample must still not earn
  a compliant‑temperature credit).
- `tests/test_api.py` — telemetry helper sends `timestamp`/`pyrolysis_temperature`; align to §2.
- Any test relying on the conftest telemetry mock (Task 5).

---

## 6. Acceptance criteria (the whole job is done only when ALL hold)
1. `backend/tests/test_client_contract.py` — **green, with both `xfail` markers deleted.**
2. `backend/tests/test_corroboration.py` + `test_corroboration_flow.py` — green.
3. `grep -c "temperatureReadingsJson\|hwAttestationJson" backend/server.py` → 0.
4. `grep -n "wet_yield_kg: float = Field(\.\.\." backend/server.py` → empty (no longer required).
5. No global `AsyncSession.execute` mock in `conftest.py`.
6. Full `cd backend && pytest -q` — **0 new failures** vs the documented Phase‑0 baseline (the two
   known pre‑existing failures may remain; no others). Record exact counts in `REMEDIATION_LOG.md`.
7. `flutter analyze` + `flutter test` — unchanged (this phase is backend‑only; the client already
   sends the canonical fields — **do not edit `lib/`**).
8. `ruff format` reports no diffs; if a migration was added, `alembic upgrade/downgrade/upgrade` clean.
9. Append a `## Phase 7‑R` section to `REMEDIATION_LOG.md` (scope, changes, disclosed test updates,
   gate output) in the existing style.

---

## 7. Out of scope — leave alone, do NOT fix here (log to FINDINGS_BACKLOG if new)
- `#8` strict `extra="forbid"` schemas on the four side‑endpoints — a **separate** phase, done *after*
  this, against the now‑verified contract.
- The `db.py` `init_db()` `dev-token` re‑seed (already filed CRITICAL).
- Ed25519 auth on `/api/v1/media` (deferred cross‑stack item).
- Any `lib/` (Dart) change. The client is the contract source of truth here.
- CORS `allow_headers` cleanup (Phase 13).

---

## 8. Optional but recommended (auditability of a money system)
Add a `provisional_reasons` column to `Batch` (JSON/Text, nullable) + a reversible Alembic migration,
and persist `Corroboration.reasons` so each non‑issuable batch records *why*. If you add it, follow
the existing migration pattern (`backend/alembic/versions/a1b2c3d4e5f6_batches_add_provisional.py`)
and include up/down + the `BatchResponse` field. If you skip it, say so in the log — don't half‑do it.
```
