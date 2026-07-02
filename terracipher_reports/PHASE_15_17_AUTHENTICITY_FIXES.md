# Post-Audit Remediation Plan — Phases 15–17 (Authenticity, Reliability, Trust-Root)

**Author's framing (CTO):** the security remediation (Phases 1–14 + R-series) took this from
"trivially forgeable" to "forgeable only by an enrolled or key-compromised device, plus one unsigned
endpoint." Good progress — but **we cannot mint real carbon credits yet.** The full brutal audit found
that the system proves evidence *exists and is well-formed*, not that it is *true*. This plan closes that
gap in priority order. Execute one phase at a time, each fully gated before the next.

## Go / No-Go for issuance
**NO-GO** until all of **Phase 15 (P0)** ships and the attestation epic (17B) has a decision. Phase 16
(P1) does not block a *pilot* but will lose real field evidence, so it ships before scale. Phase 17 (P2)
is the strategic trust-root and is cross-team.

## Priority roadmap
| Prio | Phase | Finding | Blocks issuance? | Effort |
|---|---|---|---|---|
| **P0** | 15A | `/api/v1/media` unsigned (evidence channel anonymous) | **YES** | M (cross-stack) |
| **P0** | 15B | Issuance signature not bound to `batch_uuid` | **YES** | S |
| **P0** | 15C | Credit inputs self-asserted, unbounded (yield/temp) | **YES** | S–M |
| P0- | 15D | `lab_h_corg` range not enforced at DB; H:Corg 0.4 cliff | hardening | S |
| **P1** | 16A | Cross-isolate concurrent sync, no row-lease | field data-integrity | M |
| **P1** | 16B | `file.delete()` before sync-stamp → false permanent failure | field data-loss | S |
| **P1** | 16C | 403 `unknown_device` → `FAILED_PERMANENTLY` | field data-loss | S |
| **P1** | 16D | `closeBatch` status change never enqueued | under-reporting | S |
| **P1** | 16E | `secureWipe` deletes keys after `close()` (re-open race) | key-leak/ghost-DB | M |
| P1- | 16F | v11 `STRFTIME` nulls offset timestamps; v15 migration abort | upgrade data-loss | S |
| **P2** | 17A | Ed25519 seed is software-extractable (not StrongBox/SE) | strategic | L (platform) |
| **P2** | 17B | Real Play Integrity / DeviceCheck attestation | **YES for scale** | L (cross-team) |

---

## 0. Anti-hallucination protocol (obey throughout)
1. **Verify before edit.** Run the listed grep/Read; the "Current state" must match byte-for-byte. If not, STOP.
2. **Do not invent identifiers.** Use only names quoted from real code here.
3. **Test-first where practical:** write the failing test, watch it fail for the right reason, then fix.
4. **One phase = one gate.** Backend baseline: `183 passed, 1 skipped, 1 pre-existing failure`
   (`test_p0_21_hmac_secret`). Client baseline: `flutter test` 149 passed / 2 skipped; `flutter analyze`
   0 errors. No new failures may appear.
5. Formatters at end of each phase (`ruff format`, `dart format`). Journal each phase in
   `REMEDIATION_LOG.md`; update `FINDINGS_BACKLOG.md`.

---

# Phase 15 — Authenticity (P0, release-blocking)

## 15A — Sign the media evidence channel (Ed25519)  [CRITICAL, cross-stack]

**Problem (verified):** `upload_media` (`backend/server.py:823`) has **no** `Depends(verify_signature)`;
the client `_uploadMedia` (`lib/services/sync_queue_manager.dart` ~438-498) sends no `X-Signature`.
`upload_media` then anchors the batch (`server.py:946-956`) from a raw `X-Batch-UUID` with no device
binding, and a malformed UUID → `uuid.UUID()` raises → 500 (`server.py:946`).

**Design — a dedicated media canonical (do NOT reuse `sha256(body)`; multipart bytes aren't
reproducible client-side).** Sign the *declared* file hash, not the wire body:
```
media_canonical = "POST\n/api/v1/media\n{idempotency_key}\n{x_declared_sha256_lower}\n{batch_uuid}\n{device_id}"
```
The server already recomputes the file hash and enforces `calculated == declared` (`server.py:893`), so
signing the declared hash + batch binds "this device uploaded a file with this hash for this batch."

### Tasks
1. **Server — new dependency** in `server.py` (mirror `verify_signature`, but build the media canonical):
   `verify_media_signature(request, x_device_id, x_signature, x_idempotency_key, x_declared_sha256,
   x_batch_uuid, session)` → loads the `DeviceKey`, rebuilds `media_canonical`, verifies Ed25519; 401
   on missing sig, 403 on unknown device / `signature_mismatch`. Add `device_id: str =
   Depends(verify_media_signature)` to `upload_media`.
2. **Server — ownership + input hardening:** validate `x_batch_uuid` with a try/except → **400**
   `invalid_batch_uuid` (not 500); after loading the batch, require `batch.device_id == device_id` else
   **403** `not_your_batch`. Anchor only then.
3. **Client — sign the upload** in `_uploadMedia`: build the same media canonical and set `X-Signature`
   via `CryptoSigner` (add a `signMediaUpload(idempotencyKey, declaredSha256, batchUuid)` helper to
   `crypto_signer.dart` that signs the exact string above with the device seed). Send `X-Device-Id`
   (the real device id, not an arbitrary one).
4. **Freeze the media canonical** in a comment on both sides (client producer + server verifier) so they
   never drift (this was the root cause of the Phase-7-R telemetry-key bug).

### Tests
- `backend/tests/test_media_auth.py` (new): unsigned `/media` → **401**; valid signature + matching
  hash + owned batch → **200** and anchors; wrong device (not batch owner) → **403**; tampered
  `X-Declared-SHA256` (signature over a different hash) → **403**; malformed `X-Batch-UUID` → **400**.
- Migrate existing media tests (`test_gps_corroboration.py`, `test_media_anchoring.py`, `test_api.py`
  media cases, `test_p0_25_anchor.py`) to sign via the conftest signer — disclosed; do not weaken.
- Client: extend a sync test to assert `_uploadMedia` includes a non-empty `X-Signature`.

### Gate
`grep -n "Depends(verify_media_signature)" server.py` present; new + migrated media tests green; full
backend + flutter suites 0 new failures.

---

## 15B — Bind the issuance signature to batch identity  [CRITICAL, small]

**Problem (verified):** `sign_lca_audit` (`backend/lca_engine.py:292-302`) HMACs only `audit.__dict__` —
no `batch_uuid`/`operation_id`/timestamp. Identical inputs → identical signature across different batches.

### Tasks
1. Change signature to `sign_lca_audit(audit, secret, *, batch_uuid: str)`; sign
   `json.dumps({**data, "batch_uuid": batch_uuid}, sort_keys=True)`.
2. Update the sole caller `recompute_batch_credit` (`server.py`, the `sign_lca_audit(lca, _HMAC_SECRET)`
   call) to pass `batch_uuid=str(batch.batch_uuid)`.
3. Update `test_lca_provisional.py::test_audit_is_deterministic` (calls `sign_lca_audit(a1,"test-secret")`)
   to pass `batch_uuid=`; add a case: **same inputs, different `batch_uuid` → different signature**.

### Gate
`grep -n "batch_uuid" lca_engine.py` shows it in the signed payload; new determinism/uniqueness test
green; full suite 0 new failures.

---

## 15C — Bound and cross-check the credit inputs  [HIGH]

**Problem (verified):** `YieldPayload.wet_yield_weight_kg` (`server.py:~1012`) has no upper bound;
`TelemetryPayload.temperature_readings` (`server.py:~1001`) has no per-value bound. A single field
linearly inflates credit; a constant `200.0` array passes the CH₄ gate.

### Tasks
1. `YieldPayload.wet_yield_weight_kg: Optional[float] = Field(None, gt=0.0, le=100_000.0)` (100 t/batch
   ceiling — confirm against real kiln throughput before finalizing).
2. `TelemetryPayload.temperature_readings: Optional[conlist(float)]` with per-item bound via a
   `field_validator` (each reading `-50 ≤ t ≤ 1500`), keeping `max_length=100_000`.
3. **Cross-check (defense-in-depth):** in `corroboration.derive_wet_yield`, if `kiln_gross_capacity`
   from telemetry is present and `wet_yield_weight_kg` exceeds a plausible multiple of it, return
   `None`/`implausible_wet_yield` (keeps batch PROVISIONAL). Document that the *authoritative* control
   for burn quality is hardware attestation (Phase 17B) — bounds are a floor, not a substitute.

### Tests
`test_endpoint_schemas.py`: oversized `wet_yield_weight_kg` (1e9) → 422; out-of-range temp sample
(9999) → 422. `test_corroboration.py`: implausible yield vs kiln capacity → provisional with reason.

### Gate: new tests green; full suite 0 new failures.

---

## 15D — Enforce `lab_h_corg` at the DB; decide the H:Corg 0.4 cliff  [P0-, hardening]

**Problem (verified):** `Batch.lab_h_corg` (`models.py`) is a bare nullable `Float`; the `[0.1,1.5]`
range lives only in `LabHCorgRequest`. `step3_cremain` (`lca_engine.py:138`) has a 15% discontinuity at
`h_corg == 0.4`.

### Tasks
1. Add a DB `CHECK (lab_h_corg IS NULL OR (lab_h_corg >= 0.1 AND lab_h_corg <= 1.5))` via a new reversible
   Alembic migration (follow `c3d4e5f6a7b8`'s `batch_alter_table` pattern). Mirror in the model with a
   comment.
2. **H:Corg cliff — methodology decision required** (flag to methodology owner, do not silently change
   the number): either (a) document 0.4 as an intentional CSI tier boundary, or (b) make the retained
   fraction continuous across it. Whichever — add a test pinning the chosen behavior at 0.399/0.400.

### Gate: migration up/down/up clean; range-violating direct insert rejected by DB in a test.

---

# Phase 16 — Field reliability & data-loss cluster (P1)

## 16A — Atomic outbox row-lease (stop cross-isolate double-processing)  [HIGH]
**Problem (verified):** WorkManager runs a separate isolate/`SyncQueueManager`; `_isSyncing`
(`sync_queue_manager.dart:163`) is per-instance; the outbox has only `PENDING/SYNCED/FAILED_*` — no lease.
**Fix:** before processing, atomically claim: `UPDATE sync_outbox SET status='PROCESSING' WHERE
operationId=? AND status='PENDING'` inside a transaction; only proceed if it affected 1 row; reset to
`PENDING` on transient failure, `SYNCED`/`FAILED_PERMANENTLY` terminally. **Test:** two concurrent
`kickSync()` on the same DB process one row once (assert single POST via a counting mock client).

## 16B — Stamp before delete; treat "file gone + server has hash" as success  [MEDIUM]
**Problem (verified):** `file.delete()` (`sync_queue_manager.dart:~497`) runs before `_stampMediaSynced`
(`~395`)/status=SYNCED — a crash in between → server-accepted evidence reported as permanent failure.
**Fix:** stamp `mediaSyncedAt` (and SYNCED) **before** deleting; on retry, if the local file is missing
but the server already has the declared hash (409/duplicate), treat as synced instead of throwing.
**Test:** simulate stamp-missing + file-deleted retry → row resolves SYNCED, not FAILED.

## 16C — Classify 403 as retryable, not permanent  [MEDIUM]
**Problem (verified):** `_processEntry` maps 4xx → `PermanentSyncException` → `FAILED_PERMANENTLY`;
a boot-offline/registration-outage device signs with an unenrolled key → 403 → all field records lost.
**Fix:** treat 401/403 `unknown_device`/`signature_mismatch` as **transient** (retry with backoff, and
trigger a re-registration attempt); keep 4xx *validation* (422) permanent. **Test:** a 403 response
increments retryCount and stays `PENDING`, not `FAILED_PERMANENTLY`.

## 16D — `closeBatch` must enqueue its status change  [MEDIUM]
**Problem (verified):** `yield_end_use_writers.dart:123` updates `syncStatus=CLOSED_PENDING_UPLOAD` with
no outbox row → server never learns. **Fix:** write the metadata update + a `SyncOutbox` row atomically
(reuse the `insertWithOutbox`/metadata pattern). **Test:** `closeBatch` produces a pending outbox row.

## 16E — `secureWipe`: delete keys first, block re-open, shred properly  [HIGH]
**Problem (verified):** `app_database.dart:318-343` deletes passphrase/HMAC keys **after** `close()`,
with awaits in between where `appDatabaseProvider` can re-open on the still-present passphrase → ghost DB.
`PRAGMA secure_delete` is set at wipe time (misses earlier-freed pages); WAL deleted without checkpoint.
**Fix:** (1) set a process-level "wiping" latch that makes `_openConnection` refuse to open; (2) delete
key material **before** `close()`/file deletion; (3) set `PRAGMA secure_delete=ON` in `setup:` at open
time; (4) `PRAGMA wal_checkpoint(TRUNCATE)` before closing. **Test:** a concurrent `appDatabaseProvider`
read during wipe does not resurrect the DB; keys are gone; wipe reports success only when complete.

## 16F — Migration data-loss  [P1-]
**Problem (verified/plausible):** v11 `STRFTIME('%Y-%m-%dT%H:%M:%fZ', ...)` returns NULL for `+05:30`
offset timestamps (`app_database.dart:130-131`) → harvest time lost; v15 `TableMigration` adding
`json_valid` CHECKs aborts the whole upgrade if any legacy row has non-JSON content
(`app_database.dart:158-163`). **Fix:** replace the offset branch with a parser that preserves the
instant (or leaves the row untouched rather than nulling); precede the v15 `TableMigration` with an
`UPDATE ... SET col='[]' WHERE NOT json_valid(col)` cleanup. **Test:** `test/data/local/migration_test.dart`
— an offset timestamp survives v11; a malformed-JSON row upgrades to v15 without aborting.

---

# Phase 17 — Trust-root epics (P2, cross-team — scope, don't hack)

## 17A — Hardware-bound, non-extractable device key
**Problem (verified):** `crypto_signer.dart:31-38` generates the Ed25519 seed in Dart and stores the raw
seed in secure storage → extractable on a rooted device → full impersonation. **Acceptance criteria:**
key generated *inside* Android StrongBox / iOS Secure Enclave with `extractable=false`; signing happens
in the TEE; the seed never materializes in app memory or storage. This is a platform-channel effort
(likely a small native plugin; SE only does P-256/ECDSA, not Ed25519 — so the identity curve may need to
change to ECDSA-P256, a cross-stack canonical change). Treat as an epic with a design doc, not a patch.

## 17B — Real platform attestation (already CRITICAL-OPEN)
**Problem:** `_ATTESTATION_ENFORCED=False`; `attestation_verified` hardcoded False (`server.py:157,565`).
**Acceptance criteria:** server verifies Play Integrity (Android) / DeviceCheck+App Attest (iOS) tokens
against Google/Apple keys; on success sets `attestation_verified=True`; then flip `_ATTESTATION_ENFORCED=True`
so an unverified attestation keeps the batch PROVISIONAL (`corroboration.assemble(attestation_ok=...)` is
already wired). Needs Google/Apple credentials + backend key management — cross-team.

---

## Sequencing & sign-off
1. **15A → 15B → 15C → 15D** (P0; issuance-blocking; ship together as the "authenticity" release).
2. **16A/16E** (data-integrity + key-leak) then **16B/16C/16D/16F** (field reliability).
3. **17A/17B** as tracked epics with design docs; 17B gates *scaled* issuance.
Each phase: verify → (test-first) → change → gate green (0 new failures) → `ruff`/`dart format` →
journal in `REMEDIATION_LOG.md`, update `FINDINGS_BACKLOG.md`. After 15+16, run a fresh full regression
and append a `## Post-audit Final` block; re-run the release checklist.

## Out of scope (leave alone / already handled)
Canonical JSON signing string (correct), media path-traversal (blocked), admin `compare_digest`,
device-integrity fail-closed, secure-capture temp handling, the atomic outbox for the main writers,
migration linearity, LCA unit math. Do not reformat unrelated files beyond what a phase touches.
