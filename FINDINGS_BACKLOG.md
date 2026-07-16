# Findings Backlog

## AUDIT-9: EXIF-strip bypasses GPS quarantine (accepted, needs policy)
- Where: backend/geo.py `_evaluate_anchor` / `_gps_mismatch_km`
- A photo with no EXIF GPS can never mismatch -> batch anchors to RECEIVED.
- Catches only attackers who INCLUDE wrong GPS; stripping EXIF evades review.
- Options: (a) status RECEIVED_NO_GPS + portal badge, (b) require capture-time
  GPS envelope (RequestMetadata pattern) once mobile ships it, (c) accept until
  Play Integrity attestation is enforced (DMRV_ATTESTATION_ENFORCED=1).
- Decision owner: methodology owner. No code gate changed by the audit.

- Deleted out-of-scope test_req.py as it caused collection to hang by attempting external TCP connections.
- **[RESOLVED · Phase 15] Post-audit authenticity holes.** `/api/v1/media` now Ed25519-signed +
  device-ownership bound (15A); the LCA issuance signature is bound to `batch_uuid` (15B); self-asserted
  `wet_yield_weight_kg`/`temperature_readings` are bounded (15C); `lab_h_corg` range enforced by a DB
  CHECK (15D). Locked by `test_media_auth.py`, `test_lab_hcorg_db_constraint.py`, and signature/bound
  cases in `test_lca_provisional.py`/`test_endpoint_schemas.py`. See REMEDIATION_LOG Phase 15.
- **[RESOLVED · Phase 16] Field reliability & data-loss cluster.** Outbox row-lease (16A),
  crash-safe media stamp-before-delete (16B), 401/403 retryable (16C), closeBatch enqueue + server
  metadata upsert (16D), secureWipe keys-first/re-open-latch/secure_delete@open/WAL-checkpoint (16E),
  v11 offset-timestamp + v15 malformed-JSON migration fixes (16F). See REMEDIATION_LOG Phase 16.
- **[OPEN · Phase 17, trust-root epics — cross-team] hardware-bound non-extractable device key (17A);
  real Play Integrity/DeviceCheck attestation (17B, gates scaled issuance).** See PHASE_15_17 spec.
- **[RESOLVED · Phase 11-R] Unbounded strings / request body on the strict endpoints.** Free-text string
  fields now carry `max_length`, and a Content-Length middleware caps JSON bodies at 2 MB (413) while
  giving `/api/v1/media` 12 MB headroom. Locked by `test_endpoint_schemas.py`. See REMEDIATION_LOG Phase 11-R.
- **[CRITICAL · OPEN · SECURITY TODO] Platform attestation is not actually verified.** `hw_attestation`
  blobs (Play Integrity / DeviceCheck) are accepted but never cryptographically verified, so a rooted
  device's forged blob passes. Phase 9-R removed the dead `isinstance(dict)` check that pretended to be
  a control and now logs a loud warning; enforcement is behind `server._ATTESTATION_ENFORCED` (default
  False = non-blocking "Option B"). **To close:** implement real Play Integrity/DeviceCheck signature
  verification (`attestation_verified` in `recompute_batch_credit`) and flip `_ATTESTATION_ENFORCED=True`
  so unverified-attestation batches stay PROVISIONAL ("Option A"). Requires Google/Apple credentials —
  cross-team; not a code-only fix.
- **[RESOLVED · Phase 8-R] Client-forgeable permanence (H:Corg).** `lab_h_corg` was accepted
  unauthenticated/unbounded on `BatchPayload` and cleared PROVISIONAL — a device could forge a low
  ratio for an inflated, "final" credit. Now removed from the device payload (422 via `extra="forbid"`);
  accepted only via admin-authenticated, range-checked `POST /api/v1/admin/lab-hcorg`. Also: provisional
  batches are no longer issuance-signed (`lca_signature=None`). Locked by `test_lab_hcorg_channel.py`.
  See REMEDIATION_LOG Phase 8-R.
- **[RESOLVED · Phase 11] Finding #8 — loose `payload: dict` endpoints.** `/telemetry`, `/yield`,
  `/metadata`, `/application` now use `extra="forbid"` Pydantic models with bounded lists, and the
  mistyped `is_verified: bool` auth param is `device_id: str`. Locked by `test_endpoint_schemas.py`.
  See REMEDIATION_LOG Phase 11.
- **[RESOLVED · Phase 7-R] CONTRACT-A, CONTRACT-B and the global test mock are fixed.** Credit inputs
  are now corroborated server-side (`corroboration.py` + `recompute_batch_credit`); the real client
  batch payload is accepted and PROVISIONAL until evidence lands; telemetry key mismatch fixed
  (snake `temperature_readings`); the global `AsyncSession.execute` mock removed. Pinned green by
  `test_client_contract.py` + `test_corroboration*.py`. See REMEDIATION_LOG Phase 7-R. (Original
  findings retained below for history.)

- **[CRITICAL · contract] Real client cannot sync a batch + credit inputs are temporally impossible.**
  The Flutter client's `/batches` payload (`insertBiomassSourcingWithOutbox`) never sends
  `wet_yield_kg`, `min_recorded_temp_c`, or `transport_distance_km`, but Phase 7 made all three
  `required` on `BatchPayload` → every real batch sync returns **422**. Worse, these values do not
  exist at batch-creation time: the batch is written at harvest, while yield/telemetry/application
  evidence arrive later in the workflow. Requiring them on the batch is not just a contract mismatch,
  it is temporally impossible. **Correct fix:** derive them server-side from the corroborating
  streams (`/telemetry` → min temp, `/yield` → wet yield, `/application` → transport) and mark the
  batch **PROVISIONAL** (Phase 8 flag) until each is corroborated; never issue on a client-typed
  number. Pinned by `backend/tests/test_client_contract.py::test_real_client_batch_payload_is_accepted`
  (xfail, strict).
- **[CRITICAL · contract] Telemetry temperature key mismatch.** Client writes `temperature_readings`
  (snake, `pyrolysis_writer.dart`); server reads `temperatureReadingsJson` (camel, `server.py`
  `create_batch`). In production the burn-temperature anti-fraud gate never sees real readings.
  Hidden until now because `conftest.py` globally monkeypatches `AsyncSession.execute` to return a
  fake `{"temperatureReadingsJson": [650.0]*60}` for every telemetry query. Pinned by
  `test_client_contract.py::test_telemetry_temperature_key_agreement` (xfail, strict).
- **[HIGH · test integrity] `backend/tests/conftest.py` autouse fixture mocks `AsyncSession.execute`**
  for the WHOLE suite, faking telemetry. Large parts of the "141 passing" suite verify the mock, not
  the code. Remove the global mock; let tests insert real telemetry rows. This is why CONTRACT-B went
  unnoticed across nine phases.
- **[PROCESS] No phase gate ever verified a real client payload against the real server.** Gates were
  "backend tests green + flutter tests green," each suite internally consistent but mutually drifted.
  `test_client_contract.py` (golden payloads from the Dart writers, DB mock off) is the missing gate;
  keep it green going forward.
- **[RESOLVED · Phase R2] The `db.py` `init_db()` dev-token backdoor is removed** (seed block deleted;
  `check_db.py` deleted). Locked by `tests/test_no_dev_token_seed.py`. Side effect: the pre-existing
  `test_migrations_gated` failure is fixed (it failed on the removed `enrollment_tokens` query). See
  REMEDIATION_LOG Phase R2. (Original finding retained below for history.)

- **[CRITICAL · Phase 3 residual] `backend/db.py` `init_db()` re-seeds the `dev-token` backdoor on every boot.**
  Lines 55-66 unconditionally insert an `EnrollmentToken(token="dev-token")` if absent and reset its
  `used_at = None` if present — so a permanent, always-fresh enrollment token exists in production
  regardless of Phase 3's server/client fixes. Phase 3's gate only greps `server.py` and
  `crypto_signer.dart`, so this passes the gate while the backdoor survives. `db.py` is OUT OF
  Phase 3's scope; this seeding block must be removed (or gated behind a non-prod flag) in a
  dedicated step before release. NOT fixed now per scope rules.
