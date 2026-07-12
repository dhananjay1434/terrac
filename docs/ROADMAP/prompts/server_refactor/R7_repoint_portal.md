# R7 — Repoint `portal/routes.py` imports (break the circular dependency)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 7 of 10. R1–R6 must be committed & green.
> Baseline gate: **416 passed, 2 skipped** (backend) + **19 passed** (portal). ONE commit. Do not start R8.

**What this step does:** repoint `portal/routes.py` to import from the new neutral modules (`schemas`,
`services.registry`, `services.compliance`, `services.lab`, `security`) instead of from `server`. This
is the step that **breaks the circular import knot** at the root. After this, `portal/routes.py` never
imports from `server` again, and `server.py` no longer needs the defensive last-line import trick.

**This is NOT a relocation** — it edits `portal/routes.py` (not server.py). No test files are touched.
No behavior changes. No new symbols. Just changing import sources.

---

## The four imports to repoint

There are exactly 4 places in `portal/routes.py` that import from `server`:

### 1. Module-level import block (~line 51–62)
**Current:**
```python
from server import (  # noqa: E402
    AnnualVerificationRequest,
    KilnRequest,
    OperatorTrainingRequest,
    ScaleCalibrationRequest,
    SupervisorVisitRequest,
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
```

**Replace with:**
```python
from schemas import (
    AnnualVerificationRequest,
    KilnRequest,
    OperatorTrainingRequest,
    ScaleCalibrationRequest,
    SupervisorVisitRequest,
)
from services.registry import (
    upsert_annual_verification,
    upsert_kiln,
    upsert_operator_training,
    upsert_scale_calibration,
    upsert_supervisor_visit,
)
```

### 2. Lazy import of `compliance_view` (~line 254)
**Current:**
```python
    from server import compliance_view  # reuse the ONE grading view (P2.0 coupling)
```

**Replace with:**
```python
    from services.compliance import compliance_view
```

### 3. Lazy import of `_SAFE` (~line 382)
**Current:**
```python
    from server import _SAFE  # shared identity guard
```

**Replace with:**
```python
    from security import _SAFE
```

### 4. Lazy import of `apply_lab_results` (~line 441)
**Current:**
```python
    from server import apply_lab_results  # the ONE lab-ingestion path (P2.4)
```

**Replace with:**
```python
    from services.lab import apply_lab_results
```

---

## STEP 1 — Edit `backend/portal/routes.py`

Make the four replacements above. **Do not change anything else in `portal/routes.py`.**

Also update the module docstring if it mentions importing from `server` — change it to reference the
new modules. The existing comment "P2.5: reuse the admin registry request models + upsert helpers
directly from server" (lines 47–50) should be updated to mention `schemas` and `services.registry`.

---

## STEP 2 — Verify server.py's last-line import is still needed

The last lines of server.py (~lines 2753–2762) are:
```python
from portal.routes import router as portal_router  # noqa: E402
app.include_router(portal_router)
```

This import was placed at the END of server.py specifically to dodge the circular import (portal imports
from server, so server must finish defining everything before portal loads). **After R7, portal no longer
imports from server**, so this defensive positioning is no longer necessary. However, **do NOT move it
yet** — that happens in R9 (app_factory). For now, just confirm it still works in its current position.

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import app; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
3. **G2 (portal):** `cd portal && npm run typecheck && npx vitest run` → **19 passed**; `npx vite build` → OK.
   - This is the ONE step that requires the portal gate. The TypeScript doesn't import Python, but the
     vitest tests may exercise portal endpoints that call the repointed Python imports.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R7** — repointed portal/routes.py imports → schemas/services (broke the cycle); 416/2 + 19 green`
- Commit:
  ```
  refactor(backend): repoint portal imports to schemas/services — break circular dep (P4.8/R7)

  portal/routes.py now imports from schemas, services.registry, services.compliance,
  services.lab, and security — never from server. The fragile import-order cycle is dead.
  Suite green (416 passed, 2 skipped; portal 19 passed + build OK).

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
