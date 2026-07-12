# R6 — Extract `services/` package (registry, lab, compliance, evidence helpers)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 6 of 10. R1–R5 must be committed & green. Pure relocation.
> Baseline gate: **416 passed, 2 skipped**. ONE commit. Do not start R7.

**What moves:** the shared service functions that both the admin routes (server.py) and the portal
(portal/routes.py) call. Moving these into neutral `services/` modules is what enables R7 to break
the circular `server ↔ portal` import knot.

**Four new files:**

### services/__init__.py
Empty file (makes `services` a Python package).

### services/registry.py
Symbols to move from server.py:
1. `upsert_kiln` (~line 1509)
2. `_find_by_payload_key` (~line 1536)
3. `upsert_operator_training` (~line 1551)
4. `upsert_supervisor_visit` (~line 1581)
5. `upsert_scale_calibration` (~line 1613)
6. `upsert_annual_verification` (~line 1632)

**Dependencies:**
- `json` (stdlib)
- `sqlalchemy`: `select`
- `sqlalchemy.exc`: `IntegrityError`
- `sqlalchemy.ext.asyncio`: `AsyncSession`
- `models`: `Kiln`, `OperatorTraining`, `SupervisorVisit`, `ScaleCalibration`, `AnnualVerification`
- `jsonsafe` (after R1): `_safe_json` (used by `_find_by_payload_key`)
- `_parse_dt` helper — this is a local function at line 2510. It is used ONLY by `upsert_scale_calibration`.
  **Move `_parse_dt` into `services/registry.py` as well** (it depends on `datetime`, `_as_utc` from jsonsafe,
  and raises HTTPException). Add it to the facade re-export.

### services/lab.py
Symbol to move:
1. `apply_lab_results` (~line 1469)

**Dependencies:**
- `json` (stdlib)
- `credit_engine` (after R5): `recompute_batch_credit`
- `models`: `Batch` (type hint only; the function takes `batch` as an argument)
- `sqlalchemy.ext.asyncio`: `AsyncSession`
- `typing`: `Optional`

### services/compliance.py
Symbols to move:
1. `_COMPLIANCE_CATALOG` (~line 2642) — the list of tuples
2. `compliance_view` (~line 2682)

**Dependencies:**
- `jsonsafe` (after R1): `_safe_json`
- `settings` (after R2): `_attestation_enforced`

### services/evidence.py
Symbols to move:
1. `_assert_same_uuid` (~line 2150)
2. `_assert_batch_ownership` (~line 1681)
3. `_upsert_one_to_one_evidence` (~line 1722)
4. `_recompute_if_batch_exists` (~line 1766)

**Dependencies:**
- `uuid` (stdlib)
- `sqlalchemy`: `select`
- `sqlalchemy.ext.asyncio`: `AsyncSession`
- `fastapi`: `HTTPException`, `status`
- `models`: `Batch`
- `credit_engine` (after R5): `recompute_batch_credit`

---

## STEP 1 — Create the four files

Create:
- `backend/services/__init__.py` (empty)
- `backend/services/registry.py`
- `backend/services/lab.py`
- `backend/services/compliance.py`
- `backend/services/evidence.py`

Copy each symbol **verbatim** from server.py into the appropriate file. Include all docstrings and comments.

> **`_parse_dt` note:** Move `_parse_dt` (~line 2510) into `services/registry.py`. It imports `datetime`
> and calls `_as_utc` (from jsonsafe after R1) and raises `HTTPException`. It is used only by
> `upsert_scale_calibration` (for `calibrated_at` and `valid_until` parsing).

---

## STEP 2 — Edit `backend/server.py`

1. **Delete** the following from server.py (locate by name):
   - `upsert_kiln` (~line 1509–1533)
   - `_find_by_payload_key` (~line 1536–1548)
   - `upsert_operator_training` (~line 1551–1578)
   - `upsert_supervisor_visit` (~line 1581–1610)
   - `upsert_scale_calibration` (~line 1613–1629)
   - `upsert_annual_verification` (~line 1632–1678)
   - `apply_lab_results` (~line 1469–1498)
   - `_COMPLIANCE_CATALOG` (~line 2642–2679)
   - `compliance_view` (~line 2682–2724)
   - `_assert_same_uuid` (~line 2150–2157)
   - `_assert_batch_ownership` (~line 1681–1719)
   - `_upsert_one_to_one_evidence` (~line 1722–1763)
   - `_recompute_if_batch_exists` (~line 1766–1786)
   - `_parse_dt` (~line 2510–2518)
   - Delete the section comment blocks that directly precede deleted code

2. **Add re-export imports** (after the R5 imports):
   ```python
   from services.registry import (  # noqa: F401  (R6 facade)
       _find_by_payload_key,
       _parse_dt,
       upsert_annual_verification,
       upsert_kiln,
       upsert_operator_training,
       upsert_scale_calibration,
       upsert_supervisor_visit,
   )
   from services.lab import apply_lab_results  # noqa: F401  (R6 facade)
   from services.compliance import (  # noqa: F401  (R6 facade)
       _COMPLIANCE_CATALOG,
       compliance_view,
   )
   from services.evidence import (  # noqa: F401  (R6 facade)
       _assert_batch_ownership,
       _assert_same_uuid,
       _recompute_if_batch_exists,
       _upsert_one_to_one_evidence,
   )
   ```

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import upsert_kiln, apply_lab_results, compliance_view, _assert_batch_ownership, _recompute_if_batch_exists; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
   - Watch: `test_compliance_gate_c10.py`, `test_lab_hcorg_channel.py`, `test_registry_upserts.py`,
     any test that exercises the admin upsert or lab paths.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R6** — extracted services/ (registry, lab, compliance, evidence); server.py ~1530→~1180; 416/2 green`
- Commit:
  ```
  refactor(backend): extract services/ package — server.py ~1530→~1180 LOC (P4.8/R6)

  Pure relocation, no behavior change. Registry upserts, lab ingestion, compliance
  view, and evidence helpers in neutral modules (unblocks R7 portal decoupling).
  Suite green (416 passed, 2 skipped). Facade re-exports preserve import surface.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
