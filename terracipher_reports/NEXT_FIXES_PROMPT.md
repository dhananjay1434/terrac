# Next Fixes — Remediation Prompt (Phase R2 + Phase 11)

**For the engineer/agent implementing the fix.** Written to be executed **without guessing**. Every
claim is grounded in a real file+line. Re-verify each "Current state" block *verbatim* before editing;
if it differs, **STOP** and re-read.

Two independent pieces, do them in order:
- **Phase R2 — Kill the `dev-token` backdoor** (CRITICAL; blocks release). Small, self-contained.
- **Phase 11 — Strict schemas + size bounds on the loose `dict` endpoints** (finding #8). Larger.

---

## 0. Anti-hallucination protocol
1. Verify before edit (run the listed grep/Read; the snippet must match byte-for-byte).
2. Do not invent field/column/function names. The canonical field set is the closed list in §2 of
   `CONTRACT_RECONCILIATION_PROMPT.md` and re-stated in Phase 11 §B below. Nothing outside it exists.
3. Backend-only. **Do not edit `lib/` (Dart).** The client is the wire-contract source of truth.
4. One task = one gate. Never start the next on a red gate.
5. `ruff format` at the end of each phase. Determinism rules from the runbook still hold.
6. Baseline for "0 new failures" = the current Phase-7-R result: **158 passed, 1 skipped, 2 pre-existing
   failures** (`test_migrations_gated`, `test_p0_21_hmac_secret`). No others may appear.

---

# Phase R2 — Kill the `dev-token` backdoor  `[FIX]`

## R2.1 The problem (verified)
`backend/db.py` `init_db()` runs on every boot via `server.py:153-155` (`lifespan`). Lines 55-66
unconditionally **seed** an `EnrollmentToken(token="dev-token")` and **reset its `used_at = None`**:

```python
# backend/db.py:55-66  (CURRENT — verify before editing)
    # Seed the dev-token if it doesn't exist, and reset its used_at so we can reuse it
    from models import EnrollmentToken
    from sqlalchemy.future import select

    async with SessionLocal() as session:
        result = await session.execute(select(EnrollmentToken).where(EnrollmentToken.token == "dev-token"))
        token = result.scalar_one_or_none()
        if not token:
            session.add(EnrollmentToken(token="dev-token"))
        else:
            token.used_at = None
        await session.commit()
```

`register_device` (`server.py:354-407`) is already correct (Phase 3): it rejects `used_at`/expired
tokens and consumes the token unconditionally. So the backdoor exists **only** because this block
re-mints a permanently-fresh `dev-token` every boot, in production. Anyone with the APK + knowledge of the
string can enroll unlimited devices.

**Why removal is safe (verified):**
- Tests never hit this: `conftest.py` sets `DMRV_SKIP_MIGRATIONS=1`, builds schema via
  `Base.metadata.create_all`, and does **not** run `lifespan`/`init_db`. Each test mints its own token
  via `/api/v1/admin/mint-token` (see `tests/test_enrollment.py`, `test_stub_persistence.py`, etc.).
- The real client sends a real minted `ENROLLMENT_TOKEN` (`crypto_signer.dart`, no default since Phase 3).
- Only other reference is `backend/check_db.py`, a manual script that *also* resets the dev-token AND
  reads `DeviceKey.hmac_key` — a column removed in Phase 5, so the script is already broken/dead.

## R2.2 Tasks

### Task R2-a — Remove the seed block from `init_db()`
**Verify:** `grep -n "dev-token" backend/db.py` → lines 55/60/63.
**Change (`backend/db.py`):** delete the entire seed block (the comment on line 55 through the
`await session.commit()` on line 66, plus the two now-unused local imports `EnrollmentToken` and
`select` on lines 56-57). `init_db()` keeps only the Alembic-upgrade block (lines 50-53) and then
returns. Do **not** add a flag-gated re-seed — a misconfigured flag is still a backdoor; local dev
mints a token via `/api/v1/admin/mint-token` (needs `DMRV_ADMIN_SECRET`).
**Result:** `init_db()` becomes just the migration runner:
```python
async def init_db():
    """Run Alembic migrations to head. Idempotent. No data seeding."""
    if os.environ.get("DMRV_SKIP_MIGRATIONS") != "1":
        cfg = Config(str(Path(__file__).parent / "alembic.ini"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL.replace("+asyncpg", ""))
        await asyncio.to_thread(command.upgrade, cfg, "head")
```

### Task R2-b — Delete the dead backdoor-enabler script
**Verify:** `backend/check_db.py` still reads `DeviceKey.hmac_key` (line 18) and resets the dev-token
(line 11).
**Change:** delete `backend/check_db.py`. It is a manual utility, references a column removed in
Phase 5 (so it cannot run), and its purpose is to re-open the backdoor. If a DB-inspection helper is
wanted later, it must not reset tokens and must use `DeviceKey.public_key`.

### Task R2-c — Lock it with a test
**New `backend/tests/test_no_dev_token_seed.py`:**
1. Source-guard: read `backend/db.py`; assert `"dev-token" not in db_source` (the string is gone).
2. Behavior: with a fresh test DB (the `client`/`session_factory` fixtures), assert there is **no**
   `EnrollmentToken` with `token == "dev-token"`, and that `/api/v1/register` with
   `X-Enrollment-Token: dev-token` returns **401 `invalid_enrollment_token`** (auto-signed client is
   fine; register doesn't require a signature). This pins that no code path resurrects the seed.

## R2.3 Gate
- `grep -rc "dev-token" backend --include=*.py` → **0** (both `db.py` and `check_db.py` clean/gone).
- `test -f backend/check_db.py` → absent.
- `pytest -q tests/test_no_dev_token_seed.py` → passes.
- `pytest -q` (full) → **0 new failures** vs the R2 baseline (158 passed / 2 pre-existing).
- `ruff format` on `db.py` + the new test.
- Update `FINDINGS_BACKLOG.md`: mark the `db.py` dev-token CRITICAL **RESOLVED**; journal `## Phase R2`
  in `REMEDIATION_LOG.md`.

**Intended commit:** `fix(backend): remove dev-token enrollment seed/backdoor from init_db`

---

# Phase 11 — Strict schemas + size bounds on `dict` endpoints  `[FIX]`  (finding #8)

## A. The problem (verified)
`/api/v1/telemetry`, `/yield`, `/metadata`, `/application` still accept `payload: dict` with no schema
and no size cap (`server.py` ~lines 860-950), while `/batches` is strictly validated. An attacker can
post unbounded arrays or arbitrary keys. The `is_verified: bool = Depends(verify_signature)` param is
also mistyped (the dependency returns a device-id **str**).

> **Post-Phase-7-R note:** these endpoints now call `_recompute_if_batch_exists(session, bu)` after
> persisting, and `recompute_batch_credit` reads the persisted `payload_json` via the canonical keys.
> The strict models MUST keep those canonical keys intact (`temperature_readings`, `wet_yield_weight_kg`,
> `latitude`/`longitude`) or corroboration silently breaks. Re-run `test_corroboration_flow.py` as part
> of the gate.

## B. Canonical fields per endpoint (closed set — from the Dart writers; use ONLY these)
Make identity fields required, everything else `Optional` (lenient enough for the real client AND the
existing minimal test payloads), `extra="forbid"`, and bound every list.

- **TelemetryPayload** (`pyrolysis_writer.dart`): required `telemetry_uuid`, `batch_uuid`; optional
  `kiln_gross_capacity`, `burn_start_timestamp`, `burn_end_timestamp`, `min_temp`, `max_temp`,
  `temperature_readings: list[float] = Field(None, max_length=100_000)`,
  `smoke_evidence: list[dict] = Field(None, max_length=1_000)`,
  `hw_attestation: list = Field(None, max_length=1_000)`.
- **YieldPayload** (`yield_end_use_writers.dart`): required `yield_uuid`, `batch_uuid`; optional
  `quench_methodology`, `gross_volume`, `wet_yield_weight_kg`, `dry_yield_weight_kg`.
- **MetadataPayload** (`app_database.dart`): required `batch_uuid`; optional `artisan_id`,
  `device_hardware_mac`, `app_build_version`, `sync_status`, `created_at`.
- **ApplicationPayload** (`yield_end_use_writers.dart`): required `application_uuid`, `batch_uuid`;
  optional `application_methodology`, `application_rate_tonnes`, `transport_distance_km`,
  `latitude`, `longitude`, `farmer_photo_path`, `farmer_photo_sha256`.

All four: `model_config = ConfigDict(extra="forbid")`.

## C. Tasks
1. Define the four models near `BatchPayload` in `server.py`.
2. Replace `payload: dict` with the typed models; change `is_verified: bool = Depends(verify_signature)`
   → `device_id: str = Depends(verify_signature)`. Persist `json.dumps(payload.model_dump(mode="json"))`;
   replace `payload.get("x")` with attribute access. Keep the `_recompute_if_batch_exists(session, bu)`
   calls and the identity-field handling.
3. New `backend/tests/test_endpoint_schemas.py`: for each endpoint — unknown extra field → 422; an
   oversized `temperature_readings` (100_001 items) → 422; a valid minimal payload → 201 and persists.

## D. Affected existing tests (disclose + migrate; do NOT weaken)
- `tests/remediation/test_stub_persistence.py` — sends foreign keys (`some_data`, `yield_kg`,
  `field_id`) and asserts full-dict persistence; these will now 422. Migrate to canonical fields (§B)
  and assert on real columns / round-tripped canonical keys, not arbitrary extras.
- Re-run `test_corroboration_flow.py`, `test_corroboration.py`, `test_lca_provisional.py`,
  `test_temperature_log_verification.py`, `test_lab_hcorg_ingestion.py` — they post minimal
  telemetry/yield/application; confirm the schemas accept those (they should — identity required, rest
  optional). Any failure means a field is missing from §B; add it, don't loosen `extra`.

## E. Gate
- `grep -c "payload: dict" backend/server.py` → **0**.
- `pytest -q tests/test_endpoint_schemas.py` → passes.
- `pytest -q` (full) → **0 new failures** vs baseline.
- `ruff format`; journal `## Phase 11` in `REMEDIATION_LOG.md`.

**Intended commit:** `fix(backend): strict schemas + size bounds on telemetry/yield/metadata/application`

---

## Out of scope for both (leave alone; log if new)
- Phase 12 (`getBatchTelemetryUnsafe` → `@visibleForTesting`), Phase 13 (doc claims), Phase 14 (sign-off).
- Ed25519 auth on `/api/v1/media` (deferred cross-stack item).
- CORS `allow_headers` still lists dead `X-Hmac-Signature` / omits `X-Signature` (Phase 13 hygiene).
