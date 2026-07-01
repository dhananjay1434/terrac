# Hardening Fixes — Phase 8-R, 9-R, 11-R (Remediation Prompt)

**For the engineer/agent implementing the fix.** Executable without guessing. Re-verify each
"Current state" block *verbatim* before editing; if it differs, **STOP**. These address the brutal
re-audit of Phases 8–12. Do them **one at a time, in order**, each fully gated before the next.

## 0. Anti-hallucination protocol
1. Verify-before-edit (grep/Read; snippet must match byte-for-byte).
2. Do not invent identifiers. Field/column/function names are quoted from real code below.
3. Backend-only unless a task says otherwise (the real client does **not** send `lab_h_corg` —
   `insertBiomassSourcingWithOutbox` in `app_database.dart` omits it — so removing it from the batch
   payload breaks no client path; **do not edit `lib/`**).
4. One task = one gate. `ruff format` at the end of each phase. `sort_keys`/canonical rules still hold.
5. Baseline for "0 new failures" = current: full backend **171 passed, 1 skipped, 1 pre-existing
   failure** (`test_p0_21_hmac_secret`). No others may appear.

---

# Phase 8-R — Permanence (H:Corg) must be authenticated + bounded, never client-asserted

## 8R.1 The hole (verified)
Phase 8 promised "never issue on an *assumed* permanence; require a *measured* H:Corg." But the
"measurement" is accepted, **unauthenticated and unbounded, from the device**:
- `server.py:259` — `lab_h_corg: Optional[float] = Field(None, ...)` on `BatchPayload` (no bounds).
- `server.py:663` — `create_batch` passes `payload.lab_h_corg` into `recompute_batch_credit`.
- `server.py:492-494` — `effective_lab = lab_h_corg or batch.lab_h_corg`; `has_lab_hcorg = effective_lab
  is not None` → **clears PROVISIONAL**.
- `lca_engine.py:138` — `step3_cremain`: `if h_corg_ratio >= 0.4: <conservative>` **else** the
  high-permanence (~0.96) branch. **No lower bound** — `lab_h_corg = 0.01` (or negative) takes the max
  branch.

**Attack:** device POSTs a batch with `lab_h_corg: 0.05` → non-provisional, maximally-inflated credit,
from a number the untrusted device typed in. This is the same class of bug 7-R fixed for
wet_yield/temp/transport.

## 8R.2 Fix design (chosen: authenticated lab channel)
A lab-measured value must arrive on an **admin/lab-authenticated** channel (like `mint_enrollment_token`
uses `X-Admin-Secret`), **not** the device batch payload — and be **range-validated**. The `Batch.lab_h_corg`
column already exists (Phase 7-R). No migration needed.

### Task 8R-a — Remove `lab_h_corg` from the device payload path
**Verify:** `grep -n "lab_h_corg" server.py` → lines 259, 444, 492, 524, 658, 663.
**Changes (`server.py`):**
1. Delete `lab_h_corg` from `BatchPayload` (line 259). `extra="forbid"` will now 422 any client that
   sends it (the real client doesn't).
2. In `create_batch`, drop `lab_h_corg=payload.lab_h_corg` from the `Batch(...)` constructor (line 658)
   and from the `recompute_batch_credit(...)` call (line 663) → `await recompute_batch_credit(session, batch)`.
   `recompute` will read the persisted `batch.lab_h_corg` (None for a fresh batch) via its existing
   `effective_lab = lab_h_corg if lab_h_corg is not None else batch.lab_h_corg` fallback — keep that line.
   (Keep the `recompute_batch_credit` signature's optional `lab_h_corg` param; the lab endpoint below uses it.)

### Task 8R-b — Add a bounded, admin-authenticated lab-ingestion endpoint
**Add to `server.py`** (mirror `mint_enrollment_token`'s auth exactly):
```python
class LabHCorgRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_uuid: UUID
    # Physically plausible H:Corg molar ratio for biochar. Reject absurd/forged values.
    lab_h_corg: float = Field(..., gt=0.0, ge=0.1, le=1.5)

@app.post("/api/v1/admin/lab-hcorg", status_code=status.HTTP_200_OK)
async def ingest_lab_hcorg(
    payload: LabHCorgRequest,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
    if not hmac.compare_digest(x_admin_secret, _ADMIN_SECRET):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="unauthorized")
    batch = (
        await session.execute(select(Batch).where(Batch.batch_uuid == payload.batch_uuid))
    ).scalar_one_or_none()
    if batch is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="unknown_batch")
    await recompute_batch_credit(session, batch, lab_h_corg=payload.lab_h_corg)
    await session.commit()
    return {"status": "ok", "batch_uuid": str(payload.batch_uuid), "provisional": batch.provisional}
```
> Range `[0.1, 1.5]`: biochar H:Corg is physically ~0.1–0.7; the bound rejects the `0.01` inflation
> attack and any negative/absurd value while leaving headroom. Confirm against `lca_engine` comments
> (`step3_cremain` docstring says Lantana is 0.3–0.35) before finalizing the exact bounds.

### Task 8R-c — Tests
- **New `backend/tests/test_lab_hcorg_channel.py`:**
  1. `lab_h_corg` sent on `/api/v1/batches` → **422** (extra field forbidden).
  2. `/api/v1/admin/lab-hcorg` without/with-wrong `X-Admin-Secret` → **401**.
  3. valid admin call with an out-of-range ratio (e.g. `0.01`, `-0.2`, `9.0`) → **422**.
  4. valid admin call on a fully-corroborated batch with in-range ratio → **200**, batch
     `provisional` flips **False** and `net_credit` reflects the lab ratio.
  5. admin call for an unknown batch → **404**.
- **Migrate (disclosed):**
  - `tests/remediation/test_lab_hcorg_ingestion.py` — currently posts `lab_h_corg` inside the batch
    payload. Rewrite to: corroborate the batch (telemetry+yield), create it, then set the ratio via
    `/api/v1/admin/lab-hcorg`; assert credit_low (0.1) > credit_high (0.6). Keep the intent.
  - `tests/test_lca_provisional.py::test_batch_with_lab_hcorg_is_not_provisional` — the batch payload no
    longer carries `lab_h_corg`; corroborate the batch, then set the ratio via the admin endpoint, then
    assert `provisional False`. (The engine-level tests `test_no_lab_value_is_provisional` /
    `test_lab_value_is_not_provisional` call `calculate_carbon_credit` directly and are unaffected.)

## 8R.3 Gate
- `grep -n "lab_h_corg" server.py` shows it only in `recompute_batch_credit`, the lab endpoint, and the
  `batch.lab_h_corg` fallback — **not** in `BatchPayload` or the `create_batch` payload path.
- `pytest -q tests/test_lab_hcorg_channel.py` passes; migrated tests pass.
- `pytest -q` (full) → **0 new failures**. `ruff format`. Journal `## Phase 8-R`; mark the finding
  RESOLVED in `FINDINGS_BACKLOG.md`.

**Intended commit:** `fix(backend): accept lab H:Corg only via authenticated, range-checked channel`

---

## (Fold into 8-R) Do NOT sign an issuance audit for a PROVISIONAL batch
**Verify:** `server.py:527-532` — `recompute_batch_credit` always computes `net_credit_t_co2e` and sets
`batch.lca_signature = sign_lca_audit(...)`.
**Problem:** a provisional/uncorroborated batch carries a signed audit; a downstream issuer reading
`net_credit` + `lca_signature` without gating on `provisional` could treat it as issuable.
**Change:** in `recompute_batch_credit`, only sign when **not** provisional; otherwise null the signature:
```python
    batch.net_credit_t_co2e = lca.net_credit_t_co2e
    batch.lca_methodology_version = lca.methodology_version
    batch.lca_audit_json = json.dumps({k: v for k, v in lca.__dict__.items()})
    batch.lca_signature = None if batch.provisional else sign_lca_audit(lca, _HMAC_SECRET)
```
**Test (add to 8R-c or `test_corroboration_flow.py`):** an uncorroborated batch → `lca_signature is None`
and `provisional is True`; after full corroboration + lab ratio → `lca_signature` is a non-empty string.
Check no existing test asserts a non-null signature on a provisional batch (grep `lca_signature`).

---

# Phase 9-R — Platform attestation: verify for real, or fail honestly (not silently)

## 9R.1 The hole (verified)
`server.py:478-484` (`recompute_batch_credit`) rejects only when `hw_attestation` is a **dict** with
`status == "INVALID"`. The real client sends a **list** of base64 blobs
(`lib/data/local/pyrolysis_writer.dart:132`: `attestationBlobs.map((b)=>base64Encode(b)).toList()`), so
the gate **can never fire** — a rooted device's forged blob passes. The comment "Here we would verify
Play Integrity / DeviceCheck" is an unfulfilled TODO. This is cosmetic security.

## 9R.2 Fix design
Real Play Integrity / DeviceCheck verification is a large, credential-bound integration (Google/Apple
keys) and is out of scope for a hardening pass. The honest, in-scope fix is to **stop pretending it's a
control** and make its absence explicit and reviewable — never a silent pass. Two acceptable options;
pick per product decision:

- **Option A (recommended, minimal):** treat telemetry as **uncorroborated for temperature unless a
  verified attestation is present**, and record `attestation_unverified` as a provisional reason. I.e.
  a burn with no verifiable platform attestation cannot produce a *final* credit — it stays PROVISIONAL.
  Concretely: add an `attestation_ok: bool` input to `corroboration.assemble` (or a new reason); until a
  real verifier exists, `attestation_ok` is `False` whenever `hw_attestation` is absent/unverifiable, so
  such batches are provisional. This fails **closed** and is honest.
- **Option B (defer, but stop lying):** keep it non-blocking but replace the dead dict-check with an
  explicit `log.warning("hw_attestation present but NOT verified (Play Integrity/DeviceCheck TODO)")`
  and a `# SECURITY TODO` marker, and file a CRITICAL backlog item. No false sense of a control.

**Do not** leave the current dead `isinstance(dict)` check as-is.

### Task 9R-a
Implement the chosen option in `recompute_batch_credit` (and `corroboration.assemble`/`Corroboration`
if Option A). If Option A, `derive`/`assemble` stay pure and unit-testable — add the `attestation_ok`
parameter and a `attestation_unverified` reason.

### Task 9R-b — Tests
- Option A: unit test in `test_corroboration.py` — `assemble(..., attestation_ok=False)` →
  `attestation_unverified` in reasons and `provisional True`. Flow test: telemetry without verifiable
  attestation keeps the batch provisional even when temp/yield/transport are present.
- Option B: a test asserting the warning path / backlog marker exists (source-guard for the TODO), plus
  `FINDINGS_BACKLOG.md` CRITICAL entry.

## 9R.3 Gate
- `grep -n 'isinstance(attestation, dict)' server.py` → **0** (dead check gone).
- `pytest -q` (full) → **0 new failures**. `ruff format`. Journal `## Phase 9-R`.

**Intended commit (Option A):** `fix(backend): batches without verified platform attestation stay provisional`

---

# Phase 11-R — Bound strings and total request size, not just arrays

## 11R.1 The gap (verified)
Phase 11 bounded list length but not string length or total body size:
- `TelemetryPayload`/`YieldPayload`/`MetadataPayload`/`ApplicationPayload` string fields
  (`artisan_id`, `quench_methodology`, `application_methodology`, `farmer_photo_path`, etc.) and
  `BatchPayload.feedstock_species`/`photo_path` have **no `max_length`**.
- `smoke_evidence: list[dict]` bounds the list to 1000 but each dict is free-form.
- Starlette has **no default request-body cap**, so a single huge string field is accepted.

## 11R.2 Fix
### Task 11R-a — Bound string fields
Add `max_length` to every free-text `str` field in the four Phase-11 models and the batch-adjacent
free-text fields. Suggested caps (confirm against real data): identifiers/methodologies `max_length=128`;
paths/hashes `max_length=512`; `feedstock_species` is already validated against `CORG_TABLE` (bounded by
enum) — leave it. Use `Field(None, max_length=...)`.

### Task 11R-b — Cap total request body
Add one ASGI/Starlette middleware in `server.py` that rejects oversized bodies **before** parsing:
```python
_MAX_BODY_BYTES = 2 * 1024 * 1024  # 2 MB — generous for a 100k-float telemetry log

@app.middleware("http")
async def _limit_body_size(request: Request, call_next):
    cl = request.headers.get("content-length")
    if cl is not None and cl.isdigit() and int(cl) > _MAX_BODY_BYTES:
        return JSONResponse(status_code=413, content={"detail": "payload_too_large"})
    return await call_next(request)
```
(Exempt or raise the cap for `/api/v1/media` if the 10 MB upload path flows through it — verify: media
uses multipart `UploadFile`, which already enforces its own 10 MB chunked cap, and may bypass this
middleware’s intent; set `_MAX_BODY_BYTES` appropriately or scope the check to the JSON endpoints.)
Requires `from starlette.responses import JSONResponse` (or `fastapi.responses`).

### Task 11R-c — Tests (`backend/tests/test_endpoint_schemas.py`, extend)
- an over-long string field (e.g. `artisan_id` = `"x"*10_000`) → **422**.
- a request with `Content-Length` > `_MAX_BODY_BYTES` → **413** (craft a payload just over the cap, or
  assert the middleware via a large valid-shaped body).

## 11R.3 Gate
- `pytest -q tests/test_endpoint_schemas.py` passes (incl. new string/size cases).
- `pytest -q` (full) + `flutter test` (media path unaffected) → **0 new failures**. `ruff format`.
  Journal `## Phase 11-R`.

**Intended commit:** `fix(backend): bound string fields and total request body size`

---

## Suggested order & why
1. **8-R first** — it's the release blocker (client-forgeable permanence). Fold in the provisional-signing fix.
2. **9-R** — decide Option A vs B (product call); A is the honest fail-closed choice.
3. **11-R** — DoS hardening; lowest severity, safe last.

Out of scope (unchanged): EXIF forgeability (fundamental to photo evidence; needs a different control),
Phase 13 (doc claims/CORS), Phase 14 (sign-off), committing the tree.
