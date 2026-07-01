<USER_REQUEST>
# TerraCipher / Kon-Tiki Biochar dMRV — Master Remediation Prompt

> **What this document is.** A single, self-contained instruction set for an AI
> coding agent to remediate **every** defect found across the audit reports
> (`01_SECURITY.md` → `07_PRIORITIZED_REMEDIATION.md`, `detailed_pass3.md`,
> `02_CRITICAL_BUGS.md`, `05_LCA_METHODOLOGY_INTEGRITY.md`,
> `06_REPO_HYGIENE_AND_CONFIG.md`). It is written in the **exact style** of
> `terracpher_hardening_agent_prompt.md`: phase-wise, **one task at a time**,
> read-before-edit, every change followed by a **test gate** with multiple test
> files, and a hard **"do not proceed"** rule between tasks.

---

## 0. PRIME DIRECTIVE — READ THIS BEFORE TOUCHING ANYTHING

You are remediating a Flutter/Dart mobile app + a FastAPI Python backend. This
document is your single source of truth. Obey these rules **unconditionally**:

1. **One task at a time.** Complete a task fully, run its test gate, paste the
   output, and only then start the next task. Never batch tasks.
2. **Never hallucinate file contents.** Before modifying any file, **open it and
   read it from disk**. Every block marked `CURRENT CODE (verified <date>)` is
   the exact content that existed when this prompt was written. **The codebase
   moves** — if what you find on disk differs, **STOP and re-read**, then adapt
   the change to the real code. Do not paste a snippet from this doc on faith.
3. **Verify state before fixing.** Many `detailed_pass3.md` items are **already
   fixed** in the current tree (see the "STATUS LEDGER" below). For every task,
   first confirm the defect still reproduces. If a test in the gate already
   passes, record "already remediated — verified by test X" and move on. **Do
   not re-introduce a fixed bug by blindly applying a diff.**
4. **Never skip a test gate.** Each task ends with named tests in named files.
   The gate is mandatory. Tests must be **runnable** (they live on disk under
   `backend/tests/remediation/` and `test/remediation/`). A task is "done" only
   when its gate is green AND the full regression suite still passes.
5. **No creative deviation, no scope bleed.** Implement exactly what the task
   specifies. If you believe a step is wrong, add it to "OPEN QUESTIONS" and ask
   the human — do not silently substitute your own design.
6. **Regression after every phase.** After the last task in a phase, run the
   full suites (`pytest backend/tests/ -v` and `flutter test`). A new failure in
   a previously-green test means you broke something — fix it before proceeding.
7. **Anti-hallucination guard for tests.** The provided test stubs are
   skip-guarded (`pytest.skip(...)` / `markTestSkipped(...)`) so the suite is
   **green today**. As you implement each fix, **remove that task's skip guard**
   and make the real assertions run. Never delete a test to make a gate pass.

---

## 1. CODEBASE ORIENTATION (verified paths)

```
New folder/                         ← repo root (rename to a clean slug before pilot)
├── backend/
│   ├── server.py        (515 LOC)  ← FastAPI app, all endpoints, HMAC verify
│   ├── models.py        (102 LOC)  ← SQLAlchemy 2.0 models
│   ├── db.py             (55 LOC)  ← async engine + init_db (runs alembic)
│   ├── lca_engine.py    (256 LOC)  ← 8-step CSI carbon-credit math
│   ├── .env                        ← COMMITTED SECRETS (see Phase 0)
│   ├── .env.example
│   ├── dmrv.db                     ← COMMITTED sqlite db (delete)
│   ├── alembic/versions/2033e0a7fe86_baseline.py
│   └── tests/                      ← existing pytest suite (test_p0_*, test_p1_*, ...)
│       └── remediation/            ← NEW test stubs created by this prompt
├── lib/
│   ├── main.dart         (73 LOC)
│   ├── services/
│   │   ├── crypto_signer.dart            (122 LOC)
│   │   ├── sync_queue_manager.dart       (449 LOC)
│   │   ├── location_service.dart          (86 LOC)
│   │   ├── device_integrity_service.dart  (62 LOC)
│   │   └── secure_capture_service.dart   (366 LOC)
│   └── data/local/
│       ├── app_database.dart             (409 LOC)  schemaVersion = 15
│       ├── database_provider.dart         (15 LOC)
│       └── passphrase_resolver.dart       (46 LOC)
├── test/                           ← existing flutter tests
│   └── remediation/                ← NEW dart test stubs created by this prompt
├── all_user_inputs.txt (547 KB)    ← PROMPT DUMP — delete (Phase 0)
├── longest_msg.txt     (49 KB)     ← PROMPT DUMP — delete (Phase 0)
├── build/              (62 MB)     ← committed build artifacts — untrack (Phase 0)
├── *.py at root (find_p0_12.py, fix.py, extract_*.py, ...) ← throwaway scripts — delete
└── .gitignore                      ← clean UTF-8 but env section empty (Phase 0)
```

Read-only reference files (do **not** modify): `passphrase_resolver.dart`
(secure-key pattern), `backend/tests/conftest.py` (test DB fixture).

---

## 2. STATUS LEDGER — current state of every audited item

> Confirm each with its test gate before acting. `FIXED` items get a regression
> test only (so they can never silently regress). `OPEN` items get a real fix.

| ID | Title | State on disk | Phase |
|----|-------|---------------|-------|
| SEC-1 | Self-asserted device enrollment, key overwritable | **OPEN** `server.py:196-213` | 2 |
| SEC-2 | Unknown device → global secret fallback | **OPEN** `server.py:171-178` | 2 |
| SEC-3 / LCA-1 | Credits computed for unsigned/unverified batches | **OPEN** `server.py:165-167,285` | 2 |
| SEC-4 | Mock-GPS is a client-set header | **OPEN** `server.py:162,358` + `sync_queue_manager.dart:370` | 3 |
| SEC-5 | `.env` + prompt dumps committed | **OPEN** (`.env`, `all_user_inputs.txt`, `longest_msg.txt`) | 0 |
| SEC-6 | Fail-fast on missing secret / key sizing | **PARTIAL**: fail-fast ✅ (`server.py:32-34`); hex-string key ❌ (`crypto_signer.dart:39-42,64`) | 2 |
| SEC-7 | CORS var mismatch (`DMRV_ALLOWED_ORIGIN` unset, `CORS_ORIGINS` dead) | **OPEN** `server.py:53-61` + `.env:3` | 0 |
| SEC-8 | RASP placeholder config, detection-without-enforcement | **OPEN** `device_integrity_service.dart:20,25,52` | 3 |
| SEC-9 | Info leak: media returns absolute server path | **PARTIAL**: sha log redacted ✅ (`server.py:413`); abs path returned ❌ (`server.py:476`) | 4 |
| SEC-10 | Cleartext hardcoded register endpoint | **OPEN** `crypto_signer.dart:68` | 5 |
| BUG-1 | Biomass payload rejected 422 forever | **OPEN** `sync_queue_manager.dart:213-219` + `server.py:118-119` | 1 |
| BUG-2 | 4 stub endpoints persist nothing | **OPEN** `server.py:489-515` | 1 |
| BUG-3 | `system_metadata` routed to stub | **OPEN** `sync_queue_manager.dart:219` | 1 |
| BUG-4 | `registerDevice()` hardcoded to emulator | **OPEN** `crypto_signer.dart:61-81` | 5 |
| BUG-5 | `ref.read(appDatabaseProvider)` vs `.future` | **OPEN** `sync_queue_manager.dart:63-64` | 5 |
| BUG-6 | `autoDispose`+`keepAlive`+`onDispose` contradiction | **OPEN** `database_provider.dart:10-14` | 5 |
| BUG-7 | Media↔batch anchor by non-unique sha256 → 500 | **OPEN** `server.py:319-320,460-462` | 4 |
| BUG-8 | Race recovery `scalar_one()` on wrong constraint | **PARTIAL**: pre-check ✅ (`server.py:241-251`); `scalar_one()` ❌ (`server.py:298`) | 4 |
| BUG-9 | Media requires "optional" device id | **OPEN** `server.py:431` | 4 |
| BUG-10 | `FAILED_PERMANENTLY` silent data loss | **OPEN** `sync_queue_manager.dart:168-177` | 5 |
| LCA-2 | H:Corg hardcoded 0.35, never measured | **OPEN** `server.py:264-270` + `lca_engine.py:204` | 4 |
| LCA-3 | CH4 gate on one self-reported temp | **OPEN** `lca_engine.py:168` + `server.py:104-116` | 3 |
| LCA-4 | `gross_c_sink` computed then discarded | **OPEN** `lca_engine.py:225,249` | 4 |
| LCA-5 | Transport distance trusted, no cross-check | **OPEN** `lca_engine.py:139-150` | 3 |
| LCA-6 | Constants not versioned / not tested vs standard | **OPEN** `lca_engine.py:21-47` | 6 |
| LCA-7 | No provenance / immutability on issued credit | **OPEN** `models.py:16-40` | 6 |
| P0-21 | HMAC secret defaults to `"default_secret"` | **FIXED** `server.py:32-34` | 2 (regress) |
| P0-22 | Race accepts a different second-writer payload | **FIXED** `server.py:299-304` | 4 (regress) |
| P0-23 | `get_corg` case-sensitive under-issuance | **FIXED** `lca_engine.py:87-90` | 6 (regress) |
| P0-24 | Upload OOM (no size cap) | **FIXED** `server.py:395-406` | 4 (regress) |
| P0-25 | `MediaFile` has no FK to `Batch` | **FIXED** `models.py:47` (FK ✅; anchoring still by hash → BUG-7) | 4 |
| P1-24 | CORS `*` + credentials | **FIXED** `server.py:55-61` | 0 (regress) |
| P1-25 | `@app.on_event` deprecated | **FIXED** `server.py:39-51` | — |
| P1-26 | Declared-sha256 logged in full | **FIXED** `server.py:413` | — |
| P1-27 | `CryptoSigner` static cache not invalidated on wipe | **PARTIAL**: `clear()` + `secureWipe` call ✅; no invariant test ❌ | 5 |
| P1-28 | `Random.secure()` no fail-loud guard | **FIXED** `crypto_signer.dart:33-37`, `passphrase_resolver.dart:35-39` | — |
| P2-3 | `harvest_uptime_seconds` nullable mismatch | **FIXED** `models.py:31` + `server.py:79` | — |
| P2-4 | Mutable module-level `CORG_TABLE` | **FIXED** `lca_engine.py:30` (MappingProxyType) | — |
| HYG | build/, dmrv.db, throwaway scripts committed | **OPEN** | 0 |
| DB | `init_db` runs `alembic upgrade head` on every boot | **OPEN** `db.py:48-55` | 4 |

---

## 3. PHASE MAP (execute strictly in order)

- **Phase 0 — Repo Hygiene & Config** (SEC-5, SEC-7, P1-24 regress, HYG)
- **Phase 1 — Stop the Bleeding: payload contract & persistence** (BUG-1/2/3)
- **Phase 2 — Authentication & trust gating** (SEC-1/2/3/6, LCA-1, P0-21 regress)
- **Phase 3 — Anti-fraud integrity** (SEC-4/8, LCA-3/5)
- **Phase 4 — Backend correctness** (BUG-7/8/9, SEC-9, LCA-2/4, P0-22/24/25 regress, DB)
- **Phase 5 — Client sync robustness** (SEC-10, BUG-4/5/6/10, P1-27)
- **Phase 6 — LCA audit defensibility & provenance** (LCA-6/7, P0-23 regress)

Each phase has a **FULL TEST GATE** at its end. Do not begin phase N+1 until
phase N's gate is fully green.

---

# PHASE 0 — Repo Hygiene & Config

**Why:** The product sells *trust*. Committed DB credentials, a 547 KB dump of
the entire dev prompt history, a 62 MB `build/`, and a dead CORS variable are
the cheapest, highest-embarrassment findings. Fix them first; they unblock a
safe public push.

### TASK 0.1 — Rewrite `.gitignore` so secrets/artifacts are actually ignored

**File:** `.gitignore`

**CURRENT CODE (verified):** the file is clean UTF-8 (the old NUL-byte
corruption is gone), **but** the "Environment files" section is empty — it only
ignores `*token.json*` and `*credentials.json*`. So `backend/.env`, `build/`
(line `/build` exists but the dir is already tracked), `*.db`, and the prompt
dumps are **not** effectively ignored.

**Change:** add explicit rules. Append (or replace the empty Environment block):

```gitignore
# Environment files
.env
.env.*
!.env.example
backend/.env

# Local databases & artifacts
*.db
*.sqlite
*.sqlite3
backend/uploads/
build/
.dart_tool/
.flutter-plugins
.flutter-plugins-dependencies

# Dev prompt dumps & throwaway scripts (never ship)
all_user_inputs.txt
longest_msg.txt
*_block.txt
```

**Test gate:** `pytest backend/tests/remediation/test_repo_hygiene.py -v`
- `test_gitignore_ignores_env` — `.env` matches a `.gitignore` rule.
- `test_gitignore_ignores_db_and_build` — `*.db` and `build/` are ignored.

**Do not proceed to 0.2 until both pass.**

### TASK 0.2 — Remove committed secrets, dumps, DB, build artifacts & scripts

**Actions (use `git rm --cached` to untrack without deleting working copies you
still need; delete the dumps outright):**
1. `git rm --cached backend/.env backend/dmrv.db` and untrack `build/` (`git rm -r --cached build`).
2. Delete prompt dumps: `all_user_inputs.txt`, `longest_msg.txt`, `p0_12_block.txt`.
3. Delete throwaway scripts at repo root: `check_prompt.py extract_all.py
   extract_longest.py extract_prompt.py find_current_huge.py find_huge.py
   find_p0_12.py fix.py fix_indent.py fix_more.py search_p0_12.py gradio_download_app.py`.
4. **Rotate the exposed Postgres password** (it was in git history). Document the
   rotation in `DEPLOYMENT.md`. Purging history (e.g. `git filter-repo`) is a
   human-run step — add it to OPEN QUESTIONS, do not run destructive history
   rewrites yourself.

**Test gate:** `pytest backend/tests/remediation/test_repo_hygiene.py -v`
- `test_no_prompt_dumps_present` — the two dump files are gone from the tree.
- `test_no_throwaway_scripts` — root has no `find_*.py`/`fix*.py`/`extract_*.py`.

**Do not proceed to 0.3 until both pass.**

### TASK 0.3 — Unify environment variables (SEC-7) and document required secrets

**Files:** `backend/.env.example`, `backend/server.py` (read first).

**CURRENT CODE (verified):**
- `server.py:53` reads `DMRV_ALLOWED_ORIGIN` (singular) → if unset, `allow_origins=[]`.
- `.env` sets `CORS_ORIGINS="*"` (never read) and ships stale `MONGO_URL`,
  `DB_NAME` keys from a different stack.
- `DMRV_HMAC_SECRET` is **required** (`server.py:32-34`) but is **not** in
  `.env`/`.env.example` → the server raises `RuntimeError` at import.

**Change:**
1. Settle on **`DMRV_ALLOWED_ORIGIN`** as the one CORS variable. Rewrite
   `.env.example` to document every variable the code actually reads:
   `DATABASE_URL`, `DMRV_HMAC_SECRET`, `DMRV_ALLOWED_ORIGIN`, `LOG_LEVEL`,
   `DMRV_SKIP_MIGRATIONS`. Remove `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`.
2. Add a comment that `DMRV_ALLOWED_ORIGIN` must be a single explicit origin (or
   a comma-split list if you extend the code) and **must never be `*`** when
   credentials are enabled.
3. Confirm the regression: CORS must not echo `*` with `allow_credentials=True`.

**Test gate:** `pytest backend/tests/remediation/test_repo_hygiene.py -v`
- `test_env_example_documents_required_vars` — `.env.example` contains
  `DATABASE_URL`, `DMRV_HMAC_SECRET`, `DMRV_ALLOWED_ORIGIN` and **omits**
  `MONGO_URL`/`CORS_ORIGINS`.
- `test_cors_never_star_with_credentials` (regression for P1-24) — import the
  app; assert no middleware combines `allow_origins=["*"]` with
  `allow_credentials=True`.

### PHASE 0 FULL TEST GATE
`pytest backend/tests/remediation/test_repo_hygiene.py -v` — all 6 green, and
`pytest backend/tests/ -v` shows no regression. **Do not begin Phase 1 until green.**

---

# PHASE 1 — Stop the Bleeding: payload contract & persistence

**Why:** The headline feature (capture biomass → sync) is **dead on arrival**.
The biomass payload is routed to `/batches` and rejected `422` forever (BUG-1),
and four endpoints accept data and silently discard it (BUG-2/3) while the
client marks rows `SYNCED` and deletes the local evidence — **silent permanent
data loss**.

### TASK 1.1 — Define an explicit per-table sync contract (fix BUG-1 routing)

**File:** `lib/services/sync_queue_manager.dart` (read first).

**CURRENT CODE (verified `:213-219`):**
```dart
String endpoint = 'batches';
if (entry.targetTable == 'pyrolysis_telemetry') endpoint = 'telemetry';
if (entry.targetTable == 'yield_metrics') endpoint = 'yield';
if (entry.targetTable == 'end_use_application') {
  endpoint = 'application';
}
if (entry.targetTable == 'system_metadata') endpoint = 'metadata';
```
`targetTable == 'biomass_sourcing'` is **absent** → falls through to `batches`,
whose strict schema rejects the biomass field set.

**Change:** make routing a single explicit map and **fail loudly** on an unknown
table instead of silently defaulting to `batches`:
```dart
const _endpointByTable = <String, String>{
  'system_metadata': 'metadata',
  'biomass_sourcing': 'batches',      // biomass IS the batch record
  'pyrolysis_telemetry': 'telemetry',
  'yield_metrics': 'yield',
  'end_use_application': 'application',
};
final endpoint = _endpointByTable[entry.targetTable];
if (endpoint == null) {
  throw StateError('No sync endpoint mapped for table ${entry.targetTable}');
}
```
(Decision: biomass_sourcing is the canonical batch record and routes to
`/batches`. The schema is aligned in Task 1.2.)

**Test gate:** `flutter test test/remediation/sync_routing_test.dart`
- `biomass_sourcing routes to batches`
- `unknown table throws instead of defaulting`

### TASK 1.2 — Align `/batches` schema to the real biomass payload (fix BUG-1 schema)

**File:** `backend/server.py` (read `BatchPayload` `:69-119` first).

**CURRENT CODE (verified):** `BatchPayload` has `model_config =
ConfigDict(extra="forbid", ...)` **and** a leftover literal field
`extra_field: Optional[str] = None` (`:118`). The real client biomass payload
(`app_database.dart:276-293`) carries `sourcing_uuid, moisture_compliant,
mock_location_enabled, azimuth, pitch, roll` — all rejected by `extra="forbid"`.
Also `sha256_hash` is required `min_length=64` but the client sends `null` when
no photo was attached.

**Change (pick the explicit-contract option, not blanket `extra="ignore"`):**
1. Add the real biomass fields to `BatchPayload` with correct types/optionality:
   `sourcing_uuid: Optional[str]`, `moisture_compliant: Optional[bool]`,
   `mock_location_enabled: Optional[bool] = False`,
   `azimuth/pitch/roll: Optional[float] = None`.
2. Make `sha256_hash: Optional[str] = Field(None, min_length=64, max_length=64)`
   so a photo-less sourcing row is accepted (its `status` is then handled by the
   anchoring logic in Phase 4 / Task 4.1).
3. **Delete the `extra_field` line.** Keep `extra="forbid"` so the contract stays
   strict and honest.
4. Add a **contract test** that POSTs the *actual* serialized client payload
   (copy it verbatim from `app_database.dart:276-293`) and asserts `201`/`200`,
   not `422`.

**Test gate:** `pytest backend/tests/remediation/test_biomass_contract.py -v`
- `test_real_client_biomass_payload_accepted`
- `test_photoless_biomass_accepted_null_sha`
- `test_unknown_extra_field_still_rejected` (extra=forbid intact)

### TASK 1.3 — Implement real persistence + idempotency for the four stub endpoints (BUG-2/3)

**File:** `backend/server.py` (read `:489-515` first), `backend/models.py`.

**CURRENT CODE (verified `:489-494`, identical pattern ×4):**
```python
@app.post("/api/v1/telemetry", status_code=status.HTTP_201_CREATED)
async def create_telemetry(payload: dict, is_verified: bool = Depends(verify_hmac)):
    bu = payload.get("batch_uuid")
    if bu is None or not isinstance(bu, str):
        raise HTTPException(status_code=422, detail="batch_uuid required")
    return {"status": "success", "duplicate": False}
```
Tables `PyrolysisTelemetry`, `YieldMetrics`, `EndUseApplication` exist
(`models.py:68-102`) with `payload_json: Text` + unique `batch_uuid`; there is
**no** `system_metadata` table yet.

**Change:**
1. Add a `SystemMetadataRow` model (table `system_metadata`) mirroring the client
   payload keys (`artisan_id`, `device_hardware_mac`, `app_build_version`,
   `sync_status`, `created_at`) + `operation_id` unique + server-set `received_at`.
2. For all four endpoints, replace the stub with real persistence: accept a
   validated Pydantic body (define `TelemetryPayload`, `YieldPayload`,
   `MetadataPayload`, `ApplicationPayload`, or persist the validated raw JSON to
   `payload_json` with a typed `batch_uuid`), add
   `x_idempotency_key: str = Header(..., alias="X-Idempotency-Key")`, store
   `operation_id = x_idempotency_key`, and on `IntegrityError` return
   `{"status":"success","duplicate":True}` with HTTP 200.
3. **Decision rule:** if you cannot fully implement persistence for an endpoint
   in this task, it must return **`501 Not Implemented`** — never a fake
   `200 success` (so the client keeps the data and does not delete evidence).

**Test gate:** `pytest backend/tests/remediation/test_domain_endpoints_persist.py -v`
- `test_telemetry_persists_row` / `test_yield_persists_row` /
  `test_metadata_persists_row` / `test_application_persists_row`
- `test_duplicate_idempotency_returns_200_no_double_insert`
- `test_malformed_payload_returns_422`
- `test_unimplemented_returns_501_not_fake_success` (guards against the regression)

### PHASE 1 FULL TEST GATE
`flutter test test/remediation/sync_routing_test.dart` +
`pytest backend/tests/remediation/test_biomass_contract.py
backend/tests/remediation/test_domain_endpoints_persist.py -v` all green, full
regression green. **Do not begin Phase 2 until green.**

---

# PHASE 2 — Authentication & Trust Gating

**Why:** The trust chain is circular. The client generates its own HMAC key and
registers it via an **unauthenticated** endpoint that **overwrites** any
existing device key (SEC-1). Unknown devices fall back to a single global secret
(SEC-2), and **credits are computed and stored for unsigned batches** (SEC-3 /
LCA-1). Until this phase lands, every "verified" number is meaningless.

### TASK 2.1 — Gate device enrollment behind a one-time token; forbid key overwrite (SEC-1)

**File:** `backend/server.py` (read `register_device` `:196-213` first), `models.py`.

**CURRENT CODE (verified `:196-213`):** `register_device` is unauthenticated and
does `existing.hmac_key = payload.hmac_key` with no ownership check → anyone can
hijack a device's key.

**Change:**
1. Add an `EnrollmentToken` model (token string PK, `used_at` nullable,
   `expires_at`). Tokens are minted out-of-band (admin/provisioning) — add a
   guarded admin-only mint path or a seeding script; document it.
2. `register_device` must require a valid, unused, unexpired `X-Enrollment-Token`
   header; mark it used on success (single-use).
3. **Forbid silent overwrite:** if a `DeviceKey` already exists for `device_id`,
   reject with `409` unless the request proves control of the existing key
   (signed challenge) — do **not** overwrite.
4. Per the OPEN QUESTION in the original hardening doc: confirm with the human
   whether per-device keys (recommended) or a shared MVP secret is acceptable.

**Test gate:** `pytest backend/tests/remediation/test_enrollment_auth.py -v`
- `test_register_without_token_rejected_401`
- `test_register_with_valid_token_succeeds`
- `test_enrollment_token_is_single_use`
- `test_existing_device_key_not_overwritable`

### TASK 2.2 — Reject unknown devices; remove the global-secret fallback (SEC-2)

**File:** `backend/server.py` (read `verify_hmac` `:155-194` first).

**CURRENT CODE (verified `:171-180`):**
```python
if not x_device_id:
    secret = _HMAC_SECRET.encode("utf-8")
else:
    ... device = result.scalar_one_or_none()
    if not device:
        secret = _HMAC_SECRET.encode("utf-8")
    else:
        secret = ...device.hmac_key...
```

**Change:** missing `X-Device-Id` **or** unknown `device_id` → raise
`HTTPException(403, "unknown_device")`. The per-process `_HMAC_SECRET` must not
be used to verify per-request signatures in production (keep it, if at all, only
for an explicit, documented internal path — not as a silent fallback).

**Test gate:** `pytest backend/tests/remediation/test_enrollment_auth.py -v`
- `test_missing_device_id_rejected`
- `test_unknown_device_id_rejected_403`
- `test_registered_device_valid_signature_accepted`

### TASK 2.3 — Gate credit issuance on verification (SEC-3 / LCA-1)

**File:** `backend/server.py` (read `verify_hmac` `:165-167` and `create_batch`
`:221-338` first).

**CURRENT CODE (verified):** `:165-167` — missing signature → logs a warning and
`return False` (no rejection). `:285` — `net_credit_t_co2e=net_credit` is written
regardless, only `status` flips to `"UNVERIFIED"`.

**Change (choose ONE, confirm with human):**
- **Strict (recommended):** unsigned / invalid signature → `401`/`403`, **no row,
  no credit**.
- **Quarantine:** if draft capture must be retained, store it in a separate
  `quarantine_batches` table with **no `net_credit_t_co2e` column at all** until
  it later passes verification; only then compute and persist the credit.

Either way: **`net_credit_t_co2e` must never be written for an unverified batch.**

**Test gate:** `pytest backend/tests/remediation/test_credit_gating.py -v`
- `test_unsigned_batch_rejected_or_quarantined`
- `test_unverified_batch_has_no_credit_value`
- `test_verified_batch_gets_credit`

### TASK 2.4 — Unify HMAC key encoding to raw bytes (SEC-6)

**Files:** `lib/services/crypto_signer.dart` (`:39-42,64`), `backend/server.py`
(`:180`). Read both first.

**CURRENT CODE (verified):** the client makes 32 random bytes, hex-encodes to a
64-char string, stores the **hex string**, and keys HMAC on `utf8.encode(hexKey)`
(`:64`). The server keys on `device.hmac_key.encode('utf-8')` (`:180`). It only
"works" because both sides repeat the same mistake; the effective key is the hex
*text*, not the 32 raw bytes.

**Change:** standardize on the 32 **raw** bytes as the key. Store base64url (as
`passphrase_resolver.dart` does), decode to bytes on both client and server,
HMAC on the raw bytes. Update registration to transmit the key in the agreed
encoding. Add a cross-impl test vector (a fixed key + payload → known digest)
shared by a Dart test and a Python test so the two implementations can never
silently diverge again.

**Test gate:**
- `flutter test test/remediation/crypto_signer_keysizing_test.dart`
  (`signs_with_raw_32_byte_key`, `known_vector_matches`)
- `pytest backend/tests/remediation/test_hmac_keysizing.py -v`
  (`server_verifies_raw_byte_key`, `known_vector_matches` — same vector)

### TASK 2.5 — Regression lock for P0-21 (HMAC secret default)
**Test gate:** `pytest backend/tests/remediation/test_credit_gating.py::test_missing_hmac_secret_fails_fast`
— importing the app without `DMRV_HMAC_SECRET` raises `RuntimeError` (verifies the
`server.py:32-34` fix can never regress to `"default_secret"`).

### PHASE 2 FULL TEST GATE
All Phase 2 test files green + full regression green. Confirm: an unsigned POST
to `/batches`, `/telemetry`, `/yield`, `/metadata`, `/application` is rejected
and **no `net_credit_t_co2e`** is ever written for it. **Do not begin Phase 3 until green.**

---

# PHASE 3 — Anti-Fraud Integrity

**Why:** Every fraud control is "ask the liar if they're lying." Mock-GPS is a
client-set header (SEC-4); RASP ships with placeholder cert hashes and only sets
a flag nobody enforces (SEC-8); the 35× methane penalty hinges on one
self-reported temperature (LCA-3); transport distance is trusted blind (LCA-5).

### TASK 3.1 — Assess GPS authenticity server-side, not via a client header (SEC-4)

**Files:** `backend/server.py` (`:162-163,358-359`), `lib/services/sync_queue_manager.dart` (`:370`), `lib/services/location_service.dart` (`:36`). Read first.

**CURRENT CODE (verified):** server rejects mock GPS by reading
`request.headers["x-mock-location"]` (`server.py:162`), which the client sets
from its own flag (`sync_queue_manager.dart:370`). Client check is
`pos.isMocked && kReleaseMode` (`location_service.dart:36`) → debug/sideload
builds skip it; `DemoLocationService` fabricates Delhi coords.

**Change:**
1. **Stop trusting `X-Mock-Location`.** Remove it as a *trust* input (you may keep
   it as advisory telemetry, never as the decision).
2. Assess authenticity from signals the client cannot trivially forge, server-side:
   - plausibility of `(latitude, longitude)` vs the declared application
     polygon / region;
   - speed/teleport check between consecutive batches of the same device
     (distance / Δtime);
   - server-received timestamp vs EXIF `DateTimeOriginal` skew bound;
   - (where available) platform attestation (Play Integrity / DeviceCheck).
3. Drop the `&& kReleaseMode` qualifier client-side so mock detection is reported
   in all build modes (still advisory; the server decides).

**Test gate:** `pytest backend/tests/remediation/test_mock_gps_server_side.py -v`
- `test_x_mock_location_header_is_not_trusted`
- `test_implausible_coordinates_flagged`
- `test_teleport_between_batches_flagged`

### TASK 3.2 — RASP: real config + enforced fail-closed (SEC-8)

**File:** `lib/services/device_integrity_service.dart` (`:17-53`). Read first.

**CURRENT CODE (verified):** `signingCertHashes: ['YOUR_BASE64_CERT_HASH']`,
`teamId: 'YOUR_TEAM_ID'`; `_compromised()` only sets `deviceCompromisedProvider`.

**Change:**
1. Source real `signingCertHashes`/`teamId` from build-time config
   (`String.fromEnvironment` / a non-committed `secrets.json`), never literals.
2. **Enforce:** on compromise, block capture & sync, not just flip a flag. Gate
   the capture/sync entry points (e.g. `secure_capture_service`, sync kick) on
   `!deviceCompromised`, and surface a hard-lock UX.

**Test gate:** `flutter test test/remediation/device_integrity_enforcement_test.dart`
- `compromised_flag_blocks_capture`
- `compromised_flag_blocks_sync_kick`
- `placeholder_cert_hash_absent` (no `YOUR_BASE64_CERT_HASH` literal remains)

### TASK 3.3 — Verify the full temperature log; stop trusting a single `min_temp` (LCA-3)

**Files:** `backend/lca_engine.py` (`step7_ch4_penalty :153-171`), `backend/server.py`
(`BatchPayload._validate_burn_compliance :104-116`). Read first.

**CURRENT CODE (verified):** `step7_ch4_penalty` flips between `0.005` and `30.0`
on `min_recorded_temp_c > 190 and moisture < 15`. The validator only rejects
`0 < temp < 100`; a single fabricated `200` passes. The client already captures
`temperatureReadingsJson` + `hwAttestationJson` (`tables.dart`) but the server
never receives them (the telemetry endpoint was a stub until Phase 1).

**Change:**
1. Require the telemetry endpoint (now real, Phase 1.3) to ingest the **full
   temperature sample array** (≥ a configured minimum, e.g. 60 samples) plus
   optional hardware-attestation blob.
2. Derive `min_recorded_temp_c` and compliance **server-side from the stored
   array**, not from a single client scalar. Reject burns asserting compliance
   without a qualifying log.
3. Keep the CH4 penalty math, but feed it server-derived values.

**Test gate:** `pytest backend/tests/remediation/test_temperature_log_verification.py -v`
- `test_single_sample_temp_rejected`
- `test_full_log_required_for_compliant_penalty`
- `test_min_temp_derived_from_array_not_scalar`

### TASK 3.4 — Cross-check transport distance against captured GPS (LCA-5)

**File:** `backend/lca_engine.py` (`:139-150`) + `server.py` (where
`transport_distance_km` is accepted). Read first.

**Change:** when both production GPS and application-field GPS are present,
compute the Haversine distance server-side and reject / clamp a
`transport_distance_km` that is implausibly lower than the geographic minimum
(an artisan minimizing the penalty by under-reporting). Document the tolerance.

**Test gate:** `pytest backend/tests/remediation/test_temperature_log_verification.py::test_under_reported_transport_flagged`

### PHASE 3 FULL TEST GATE
All Phase 3 tests + regression green. **Do not begin Phase 4 until green.**

---

# PHASE 4 — Backend Correctness

**Why:** Anchoring by a non-unique content hash can 500 and mis-bind (BUG-7); a
race can `NoResultFound`-500 (BUG-8); media upload demands an "optional" device
id (BUG-9); the permanence factor is hardcoded (LCA-2); dead intermediate math
confuses auditors (LCA-4); migrations run on every boot (DB); the API leaks the
server filesystem path (SEC-9).

### TASK 4.1 — Anchor media to batch by explicit `batch_uuid`, not by sha256 (BUG-7, P0-25)

**File:** `backend/server.py` (`:316-328`, `:459-469`), `models.py` (`:47`). Read first.

**CURRENT CODE (verified):** both anchoring sites use
`select(...).where(MediaFile.sha256_hash == ...)` / `Batch.sha256_hash == ...`
with `scalar_one_or_none()`. `sha256_hash` is **not unique** on either table →
two rows with the same photo hash raise `MultipleResultsFound` → HTTP 500, and
reused photos anchor to the wrong batch. `MediaFile.batch_uuid` FK already exists.

**Change:**
1. The client must supply the parent `batch_uuid` on the media upload (add header
   `X-Batch-UUID` or a field). Anchor `MediaFile.batch_uuid = <supplied uuid>`
   directly via the FK.
2. Remove both `sha256_hash`-based lookups. Keep `sha256_hash` only for integrity
   verification of the bytes, never as a join key.
3. Replace `scalar_one_or_none()` content-hash joins entirely.

**Test gate:** `pytest backend/tests/remediation/test_media_anchoring.py -v`
- `test_media_anchors_by_explicit_batch_uuid`
- `test_duplicate_photo_hash_does_not_500`
- `test_reused_photo_anchors_to_correct_batch`

### TASK 4.2 — Constraint-aware race recovery (BUG-8, regress P0-22)

**File:** `backend/server.py` (`:290-314`). Read first.

**CURRENT CODE (verified `:296-298`):** after `IntegrityError`, re-selects by
`batch_uuid` and calls `scalar_one()`. If the violation was on `operation_id`
(same idempotency key, different `batch_uuid`), the `batch_uuid` lookup returns
nothing → `NoResultFound` → unhandled 500.

**Change:** inspect which unique constraint was violated (or try both lookups):
- `operation_id` collision with a different `batch_uuid` → `409 conflict`.
- `batch_uuid` collision → return the existing row (current behavior) only after
  the Phase-2/P0-22 payload-equality check (`:299-304`) — keep that intact.
Never let `scalar_one()` raise unhandled.

**Test gate:** `pytest backend/tests/remediation/test_race_constraints.py -v`
- `test_operation_id_collision_returns_409_not_500`
- `test_batch_uuid_duplicate_same_payload_returns_existing`
- `test_race_with_different_payload_returns_409` (P0-22 regression)

### TASK 4.3 — Make the media device-id contract honest (BUG-9)

**File:** `backend/server.py` (`:346-352,419-432`). Read first.

**CURRENT CODE (verified):** `x_device_id: Optional[str] = Header(None, ...)`
(`:352`) but `_safe_device(x_device_id)` (`:431`) runs `_SAFE.match(s or "")` →
`None`/empty fails → `400 invalid_device_id`. The "optional" typing lies.

**Change:** decide the contract. Recommended: make `X-Device-Id` **required**
(`Header(..., alias="X-Device-Id")`) consistent with HMAC verification, returning
a clear `422` when missing. If genuinely optional, branch so a missing id stores
the file under an `anon/` namespace without raising.

**Test gate:** `pytest backend/tests/remediation/test_media_anchoring.py -v`
- `test_media_missing_device_id_clear_error`
- `test_media_with_device_id_succeeds`

### TASK 4.4 — Ingest lab-measured H:Corg; stop defaulting 0.35 (LCA-2) & remove dead gross math (LCA-4)

**Files:** `backend/server.py` (`create_batch :263-271`), `backend/lca_engine.py`
(`:101-106,109-127,204,224-225,239-256`). Read first.

**CURRENT CODE (verified):** `calculate_carbon_credit(...)` is called **without**
`h_corg_ratio` (`server.py:264-270`) → always defaults to `0.35`, so every batch
is credited as top-tier-stable biochar. `BatchPayload` has no H:Corg field.
`step2_gross_c_sink` is computed and stored but never used in the net result.

**Change:**
1. Add a lab-data ingest path: a `h_corg_ratio` field on the batch/lab payload
   (or a dedicated lab-result upload) and pass it through to
   `calculate_carbon_credit`. **Reject issuance** (or quarantine, consistent with
   Task 2.3) when no lab-measured H:Corg is present — do not silently assume 0.35.
2. Either remove `gross_c_sink` from the net path entirely or clearly annotate it
   `# audit-only, intentionally not part of net` and assert in a test that net
   derives solely from `cremain` (so no future refactor double-applies 44/12).

**Test gate:** `pytest backend/tests/remediation/test_hcorg_ingest.py -v`
- `test_missing_hcorg_does_not_issue_default_035`
- `test_provided_hcorg_flows_into_credit`
- `test_net_credit_independent_of_gross_c_sink` (LCA-4 guard)

### TASK 4.5 — Stop leaking the server filesystem path (SEC-9)

**File:** `backend/server.py` (`MediaUploadResponse :131-134`, `:445,476`). Read first.

**CURRENT CODE (verified):** `MediaUploadResponse.file_path` returns
`str(file_path)` — the absolute server path — to the client (`:476`).

**Change:** return an opaque identifier (the `operation_id` or a storage key),
not the absolute path. Keep the absolute path only in the DB / logs.

**Test gate:** `pytest backend/tests/remediation/test_media_anchoring.py::test_response_does_not_leak_abs_path`

### TASK 4.6 — Gate migrations; stop running `alembic upgrade head` on every boot (DB)

**File:** `backend/db.py` (`init_db :48-55`). Read first.

**CURRENT CODE (verified):** `init_db` runs `alembic upgrade head` in a thread on
startup and does `DATABASE_URL.replace("+asyncpg","")` — brittle for non-asyncpg
URLs (e.g. `sqlite+aiosqlite` stays async → mismatch).

**Change:** make boot-time migration **opt-in** via env (e.g.
`DMRV_RUN_MIGRATIONS=1`), default **off** in production (migrations are a
reviewed deploy step). Replace the string `.replace` with a proper sync-URL
derivation (driver-aware). Keep `DMRV_SKIP_MIGRATIONS` semantics consistent.

**Test gate:** `pytest backend/tests/remediation/test_migration_gating.py -v`
- `test_migrations_not_run_by_default`
- `test_sync_url_derivation_handles_sqlite_and_postgres`

### PHASE 4 FULL TEST GATE
All Phase 4 tests + regression green. **Do not begin Phase 5 until green.**

---

# PHASE 5 — Client Sync Robustness

**Why:** Registration is hardcoded to the emulator over plaintext (BUG-4/SEC-10);
the sync constructor uses an `AsyncValue` where it needs the resolved DB
(BUG-5); the DB provider self-contradicts (BUG-6); 11 retries silently abandon
rural offline data (BUG-10); and the static signing-key cache can survive a wipe
(P1-27).

### TASK 5.1 — Env-driven HTTPS device registration (BUG-4, SEC-10)

**File:** `lib/services/crypto_signer.dart` (`registerDevice :61-81`). Read first.

**CURRENT CODE (verified `:67-68`):**
```dart
final response = await http.post(
  Uri.parse('http://10.0.2.2:8000/api/v1/register'),
```
Hardcoded emulator loopback, plaintext, fixed port → never runs in production;
leaks the key over cleartext on the dev path.

**Change:** build the URL from the same env base the sync layer uses
(`String.fromEnvironment('DMRV_API_BASE_URL')`), enforce HTTPS in release, and
make registration part of a real, awaited enrollment flow that retries (and that
now sends the `X-Enrollment-Token` from Task 2.1). Remove the literal `10.0.2.2`.

**Test gate:** `flutter test test/remediation/register_device_env_test.dart`
- `register_uses_env_base_url`
- `release_requires_https`
- `no_hardcoded_emulator_loopback`

### TASK 5.2 — Fix the `FutureProvider` misuse and provider lifecycle (BUG-5, BUG-6)

**Files:** `lib/services/sync_queue_manager.dart` (`:63-64`),
`lib/data/local/database_provider.dart` (`:10-15`). Read first.

**CURRENT CODE (verified):**
```dart
// sync_queue_manager.dart:63-64
final db = ref.read(appDatabaseProvider);      // AsyncValue<AppDatabase>
_dbSubscription = db.tableUpdates(...).listen(...); // tableUpdates not on AsyncValue
```
```dart
// database_provider.dart:10-15
final appDatabaseProvider = FutureProvider.autoDispose<AppDatabase>((ref) async {
  ref.keepAlive();                 // negates autoDispose
  final db = AppDatabase();
  ref.onDispose(db.close);         // effectively never runs
  return db;
});
```

**Change:**
1. In the constructor, resolve the DB asynchronously (`await
   ref.read(appDatabaseProvider.future)`) before subscribing to `tableUpdates`,
   or move the subscription into an async init method. The current path is a
   type error waiting to crash.
2. Make the provider's lifecycle coherent: either a plain `FutureProvider`
   (kept alive, no `onDispose(close)` pretense) or genuinely `autoDispose` with a
   real close. Pick one; document the wipe-race handling explicitly.

**Test gate:** `flutter test test/remediation/sync_provider_future_test.dart`
- `db_subscription_uses_resolved_database`
- `provider_lifecycle_is_consistent` (no keepAlive + onDispose(close) contradiction)

### TASK 5.3 — Make permanent sync failures visible & recoverable (BUG-10)

**File:** `lib/services/sync_queue_manager.dart` (`:167-191`). Read first.

**CURRENT CODE (verified `:168-177`):** `retryCount > 10` →
`status='FAILED_PERMANENTLY'`, silently, with no user surface; `retryCount`
increments on *every* failure including transient ones.

**Change:**
1. Distinguish permanent (4xx contract) from transient (network/5xx) failures —
   only the former should count toward a dead state; transient failures keep
   retrying with capped jittered backoff.
2. Surface `FAILED_PERMANENTLY`/`DEAD` rows to the user (a dashboard badge / list)
   with a manual "retry" affordance. No silent abandonment of MRV evidence.

**Test gate:** `flutter test test/remediation/sync_retry_recovery_test.dart`
- `transient_failure_does_not_count_toward_dead`
- `permanent_4xx_marks_dead_with_reason`
- `dead_rows_are_user_recoverable`

### TASK 5.4 — Invalidate the static signing-key cache on wipe (P1-27)

**Files:** `lib/services/crypto_signer.dart` (`:16-21,109-114`),
`lib/data/local/app_database.dart` (`secureWipe :314-339`). Read first.

**CURRENT CODE (verified):** `secureWipe` calls `ctx.clearHmacKey()` (`:338`) and
`CryptoSigner.clear()` resets `_keyFuture`. The behavior is mostly correct but
**untested** — there is no invariant guaranteeing every wipe path invalidates the
static cache.

**Change:** add the invariant test (below). Optionally make `CryptoSigner`
instance-based + injected via Riverpod to remove the static cache entirely
(larger refactor — gate behind an OPEN QUESTION).

**Test gate:** `flutter test test/remediation/crypto_signer_keysizing_test.dart`
- `wipe_invalidates_static_key_cache` — after the production wipe path, signing the
  same payload yields a **different** signature (new key) — proving no stale key.

### PHASE 5 FULL TEST GATE
All Phase 5 tests + regression green. **Do not begin Phase 6 until green.**

---

# PHASE 6 — LCA Audit Defensibility & Provenance

**Why:** The LCA code is clean but **unaudited against the standard** and the
issued credit is mutable and unsigned. A registry auditor rejects both.

### TASK 6.1 — Version & pin LCA constants; test against the standard's worked examples (LCA-6, regress P0-23)

**File:** `backend/lca_engine.py` (`:21-47,87-90`). Read first.

**CURRENT CODE (verified):** constants (`SAFETY_DEDUCTION_KG_PER_T=20.0`,
`TRANSPORT_FACTOR_KG_PER_T_KM=0.01194`, decay coefficients `0.1787,-0.5337,
0.8237,-0.00997`, per-species `Corg`) are hardcoded with PDF comments but no
version pin and no fixtures derived from the standard's own examples.

**Change:**
1. Add a `METHODOLOGY_VERSION` constant (e.g. `"CSI Global Artisan C-Sink 3.2"`)
   and stamp it on every issued credit (used in Task 6.2).
2. Add a fixtures file reproducing at least one **published worked example** from
   the CSI standard; assert the engine reproduces it within tolerance.
3. Keep constants in one clearly-cited block; make the per-methodology values
   configurable by version.

**Test gate:** `pytest backend/tests/remediation/test_lca_standard_examples.py -v`
- `test_reproduces_published_example_within_tolerance`
- `test_methodology_version_is_stamped`
- `test_corg_lookup_case_insensitive` (P0-23 regression)

### TASK 6.2 — Immutable, signed, reproducible credit provenance (LCA-7)

**Files:** `backend/models.py` (`Batch :16-40`), `backend/server.py`. Read first.

**Change:**
1. Persist the **full input set** + `METHODOLOGY_VERSION` used to compute each
   credit (so the number is reproducible from stored inputs).
2. Make the issued `net_credit_t_co2e` immutable once written: add a signed audit
   record (server-side HMAC/signature over `{inputs, version, result, timestamp}`)
   and reject silent recomputation/overwrite of historical rows.
3. Provide a recompute-and-verify path that re-runs the engine on stored inputs
   and asserts the stored result matches (drift detector).

**Test gate:** `pytest backend/tests/remediation/test_credit_provenance.py -v`
- `test_credit_record_stores_inputs_and_version`
- `test_recompute_reproduces_stored_credit`
- `test_issued_credit_is_immutable`

### PHASE 6 FULL TEST GATE
All Phase 6 tests + the entire regression suite (`pytest backend/tests/ -v` and
`flutter test`) green.

---

## 4. COMPLETION CRITERIA

The remediation is complete when:
- Every Phase 0–6 test file under `backend/tests/remediation/` and
  `test/remediation/` is green with **no remaining skip guards**.
- `pytest backend/tests/ -v` and `flutter test` pass with zero failures.
- The STATUS LEDGER has no `OPEN`/`PARTIAL` rows left (each is `FIXED` + covered
  by a regression test).
- No secret, prompt dump, build artifact, or throwaway script remains tracked.
- Every issued `net_credit_t_co2e` is verified, reproducible, version-stamped,
  and immutable.

## 5. OPEN QUESTIONS — flag to the human, do NOT resolve unilaterally
1. **Enrollment model (Task 2.1/2.4):** per-device unique keys (recommended) vs a
   single shared `DMRV_HMAC_SECRET` for the MVP?
2. **Trust gating (Task 2.3):** strict reject vs quarantine-without-credit for
   unsigned batches?
3. **Git history purge (Task 0.2):** who runs `git filter-repo` to scrub the
   leaked `.env` and prompt dumps from history, and when?
4. **H:Corg source (Task 4.4):** lab-result upload endpoint vs a per-batch field —
   and what is the acceptable issuance behavior when no lab value exists?
5. **GPS attestation (Task 3.1):** is Play Integrity / DeviceCheck in scope for
   the pilot, or are server-side plausibility/teleport checks sufficient for now?

## 6. PROMPT TEMPLATE (for any task you add later)
```
### TASK N.M — <one-line title>  (<issue id>)
**File:** <exact path>  (read first)
**CURRENT CODE (verified):** <paste the exact lines you find on disk>
**Change:** <numbered, concrete steps; exact names/paths; last step = wiring>
**Test gate:** <test file path>
- <test name — what it asserts>
**Do not proceed until green.**
```
Rules: name a real file; pin versions; always include a negative test; end with a
"do not proceed" gate; one task per session; never combine tasks.

</USER_REQUEST>
<ADDITIONAL_METADATA>
The current local time is: 2026-06-28T22:49:04+05:30.
</ADDITIONAL_METADATA>