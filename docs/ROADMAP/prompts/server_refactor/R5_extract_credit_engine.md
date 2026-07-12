# R5 — Extract `credit_engine.py` (the 450-LOC recompute core)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 5 of 10. R1–R4 must be committed & green. Pure relocation.
> Baseline gate: **416 passed, 2 skipped**. ONE commit. Do not start R6.

**What moves:** the entire recompute pipeline — the coalescing wrapper, the 369-line impl, the state
management, the LCA signature verifier, and the device-registration helper. This is the crown jewel of
the backend; move it byte-for-byte with zero logic changes.

**Symbols to move (in server.py order):**
1. `_recompute_state: dict = {}` (~line 1020) — **MUTABLE DICT** (SOP §1: re-exported reference is same object)
2. `_RECOMPUTE_STATE_CAP = 8192` (~line 1021)
3. `_recompute_slot` (~line 1024)
4. `recompute_batch_credit` (~line 1040, the coalescing wrapper)
5. `_recompute_run_count = 0` (~line 1071) — **MUTABLE** integer (used as a counter in tests)
6. `_device_registered_at` (~line 1074)
7. `_recompute_batch_credit_impl` (~lines 1087–1455, **369 LOC** — the biggest function in the file)
8. `verify_lca_signature` (~line 1456)

**Dependencies `_recompute_batch_credit_impl` uses (read from its body):**
- `models`: `Batch`, `PyrolysisTelemetry`, `YieldMetrics`, `EndUseApplication`, `MoistureReading`,
  `CompositePileSample`, `TransportEvent`, `DeviceKey`, `Kiln`, `ScaleCalibration`, `AnnualVerification`,
  `SystemMetadata`
- `corroboration`: `assemble`, `derive_*` (all the derive functions imported at server.py top)
- `lca_engine`: `calculate_carbon_credit`, `sign_lca_audit`, `lca_sign_payload_bytes`, `CORG_TABLE`
- `emission_factors`: `TRANSPORT_EVENTS_ENFORCED`, `fuel_emissions_kg_co2e`
- `hmac_keys`: `active_key()`
- `observability`: `timed_recompute` decorator
- `jsonsafe` (after R1): `_safe_json`, `_safe_json_async`, `_as_utc`
- `geo` (after R1): `haversine_km`
- `settings` (after R2): `_attestation_enforced`, `log`
- `attestation` module
- `storage`: `get_storage`
- `sqlalchemy`: `select`, `desc`, `func`
- `asyncio`: `Lock` (used in `_recompute_slot`)
- `json`, `datetime`, `timezone`, `timedelta`, `uuid`

> **IMPORTANT**: `_recompute_run_count` is an integer, not a dict. When re-exported from server.py,
> `server._recompute_run_count` will be a snapshot (Python re-binds ints on assignment). Tests that
> check `server._recompute_run_count` actually read it via `server.credit_engine._recompute_run_count`
> path OR via the module global. Check if any test reads `server._recompute_run_count` — if so, you
> need the facade to do `from credit_engine import _recompute_run_count` AND the test must still see
> updates. The simplest approach: make it a mutable container `_recompute_run_count_box = [0]` or just
> keep a reference. **However** — check if tests actually reference this. If no test imports it, just
> move it and re-export. If a test does, wrap it in a list `[0]` in both the old and new location.
> **First check:** `grep -rn "_recompute_run_count" backend/tests/`

---

## STEP 1 — Create `backend/credit_engine.py`

Create `backend/credit_engine.py`. Copy ALL 8 symbols verbatim from `server.py`.

The file should have:
1. Module docstring
2. `from __future__ import annotations`
3. All imports that the moved functions need (see dependency list above)
4. The 8 symbols in the same order they appear in server.py

> **Do NOT confuse this with `lca_engine.py`** (which already exists and does the pure carbon math).
> `credit_engine.py` is the DB-glue layer that reads evidence, calls `lca_engine.calculate_carbon_credit`,
> and updates the batch row.

---

## STEP 2 — Edit `backend/server.py`

1. **Delete** the 8 symbol definitions from server.py (~lines 1020–1466).

2. **Add re-export import** (after the R4 imports):
   ```python
   from credit_engine import (  # noqa: F401  (R5 facade)
       _RECOMPUTE_STATE_CAP,
       _device_registered_at,
       _recompute_batch_credit_impl,
       _recompute_run_count,
       _recompute_slot,
       _recompute_state,
       recompute_batch_credit,
       verify_lca_signature,
   )
   ```

3. **Check now-dead imports.** After this move, server.py may no longer directly use many of the
   `corroboration.derive_*` imports, `emission_factors`, `attestation`, or `storage`. **Only remove
   if grep confirms zero remaining uses in server.py** — several are still used by `create_batch`
   (which stays in server.py until R8).

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import recompute_batch_credit, verify_lca_signature, _recompute_state, _recompute_batch_credit_impl; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
   - Watch: `test_hmac_keys.py` (imports `verify_lca_signature`), `test_p3_7_perf.py` (imports
     `_recompute_batch_credit_impl`, `_recompute_state`, `recompute_batch_credit`), and every test
     that triggers a credit recompute via a full HTTP round-trip.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R5** — extracted credit_engine.py (450-LOC recompute core); server.py ~1980→~1530; 416/2 green`
- Commit:
  ```
  refactor(backend): extract credit_engine.py recompute core — server.py ~1980→~1530 LOC (P4.8/R5)

  Pure relocation, no behavior change. The 369-line _recompute_batch_credit_impl
  is now independently importable. Suite green (416 passed, 2 skipped).
  Facade re-exports preserve `from server import ...` for tests + portal.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
