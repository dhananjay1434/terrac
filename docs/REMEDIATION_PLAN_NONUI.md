# Kon-Tiki dMRV — Production Remediation Plan (non-UI, Rainbow-independent)

*Owner: Head of Engineering. Scope: every ship-blocker from the 2026-07-03 audit that
can be closed **without** input from Rainbow. UI/UX is tracked separately
(`UX_FIELD_THEME_SPEC.md`, `UX_EXECUTION_PLAN.md`). Rainbow-blocked items are listed in
§9 and are explicitly **out of scope** here.*

---

## 1. Engineering standards (the rules every slice below obeys)

These are non-negotiable and make the plan safe to execute incrementally.

1. **One concern per PR.** Each numbered item (e.g. `P1.a`) is exactly one PR. No
   drive-by changes. A PR that grows two concerns gets split.
2. **Test-first, and the test must fail before the fix.** Every item lists the test(s)
   it adds. Write the test, watch it fail (proves it catches the bug), then fix, then
   watch it pass. A fix with no failing-first test is not done.
3. **Definition of Done (DoD), applied to every PR:**
   - New/updated tests added and green; the *whole* suite green (`pytest` + `flutter test`).
   - `ruff` + `black --check` + `mypy` (backend) and `flutter analyze` (client) clean.
   - If schema changed: Alembic `upgrade head` → `downgrade -1` → `upgrade head` round-trips
     **on PostgreSQL**, not just SQLite (see P0.c).
   - No new `TODO(security)` / silent `except` introduced.
   - CI green (CI itself is built in P0.b, so this rule activates after P0).
4. **Additive-only & fail-loud, preserved from the Rainbow protocol.** Migrations add,
   never destructively alter shipped columns. The provisional model still *never rejects
   an upload* — enforcement changes only affect the `provisional`/issuance decision, and
   every new gate ships **behind a flag defaulted to its current behavior**, flipped ON in
   a separate, isolated commit (one-phase = one-gate = one-commit).
5. **Feature-flag every enforcement change.** Reuse the existing `_ENFORCED` switch idiom.
   Wiring a gate (plumbing) and enforcing it (flip) are two separate PRs, so a bad flip
   is a one-line revert with zero code rollback.
6. **No secret, key, or `.env` ever committed.** (Verified currently clean — keep it that way.)

**Refactor policy:** refactors that de-risk a fix are welcome *inside that fix's PR only
if mechanical and covered by existing tests*; larger structural refactors get their own
PR immediately before the feature PR that needs them (called out explicitly below, e.g.
`P1.c` extracts a single gate-assembly function before wiring new gates through it).

---

## 2. Sequencing logic (why this order)

A CTO does not fix the most exciting bug first. Order is by **dependency and blast-radius**:

1. **Phase 0 — Safety net.** Build CI + a PostgreSQL test lane + fix the one broken guard
   test *before touching product code*, so every later change is automatically verified on
   the database we actually deploy. Without this, every fix below is unverified.
2. **Phase 1 — Credit correctness.** The product's core promise is a *trustworthy* credit.
   These are small, self-contained, high-value, and need no Rainbow. Fix what's already
   "done" but wrong before building anything new on top.
3. **Phase 2 — Security hardening.** Cheap, isolated, mostly middleware/startup.
4. **Phase 3 — Data integrity at scale.** Races, FKs, atomicity — the things SQLite tests
   hide and Postgres+concurrency will expose.
5. **Phase 4 — Client robustness.** Field-failure modes (BLE garbage, poison messages,
   client-side trust). Some items pair with backend changes from earlier phases.
6. **Phase 5 — Deployability/ops.** Containerize, pool, observe. Depends on nothing above,
   but is sequenced here because a pilot can run without it and it's the largest surface.
7. **Phase 6 — Mobile release enablement.** Keystore/signing; independent, can parallelize.

**Critical path to "can issue a trustworthy credit in a supervised pilot":**
`P0.a → P0.b → P0.c → P1.a → P1.b → P1.c → P1.d`. Everything else hardens or scales that.

**Critical path to "can deploy at all":** `P0.b → P5.a → P5.b → P5.c`.
**Critical path to "can release the app":** `P6.a` (independent, start anytime).

---

## 3. Phase 0 — Safety net & baseline

> Goal: make all subsequent work automatically verified on the real DB. No product-logic
> changes in this phase.

### P0.a — Fix the broken startup-guard test *and* the guarantee behind it  · size S
- **Problem:** `test_p0_21_hmac_secret` fails because `load_dotenv()` (server.py:84) re-reads
  a local `.env`, silently undoing the test's `monkeypatch.delenv`. The "refuses to start
  without a secret" guarantee is real but the test can't prove it, and the guard is weaker
  than advertised (a stray `.env` satisfies it).
- **Fix:** make secret loading deterministic and test-controllable — e.g. `load_dotenv()`
  only when `DMRV_ENV != "test"` / when not already set, and have the guard assert on the
  *resolved* config object, not raw `os.environ`. Refactor secret resolution into one
  `load_settings()` function (pydantic-settings) so there is a single source of truth.
- **Tests:** the existing test now genuinely fails-then-passes; add a test that a present
  `.env` does **not** mask a missing required var in `test` env.
- **DoD gate:** full suite green with and without a `.env` on disk.

### P0.b — Backend CI (the gate everything else depends on)  · size M
- **Fix:** `.github/workflows/backend-tests.yml` — on every PR/push: install, `ruff`,
  `black --check`, `mypy`, `pytest -q` with coverage, fail under a coverage floor (start at
  current %, ratchet up). Add `flutter analyze` + `flutter test` to the existing workflow
  (or a sibling). Branch protection: red CI blocks merge.
- **Tests:** N/A (this *is* the test harness); verify by opening a throwaway red PR.
- **DoD gate:** CI runs and blocks a deliberately-broken PR.

### P0.c — PostgreSQL test lane + migration round-trip  · size M
- **Problem:** every functional test runs on SQLite with `DMRV_SKIP_MIGRATIONS=1`; the
  Postgres DDL is **never exercised**, and Float/constraint/boolean behavior differs.
- **Fix:** add a CI job using a `postgres` service (or `testcontainers`). Run: (1) Alembic
  `upgrade head` from empty, (2) `downgrade base`, (3) `upgrade head` again — must succeed;
  (4) run a tagged smoke subset of the suite against Postgres (not SQLite). Add a
  `pytest` marker `@pg` for tests that must run on Postgres.
- **Tests:** the migration round-trip *is* the test; tag ~10 highest-value integration
  tests `@pg`.
- **DoD gate:** migration round-trip green on Postgres in CI; documents the real
  prod-parity baseline.

---

## 4. Phase 1 — Credit-integrity correctness (highest value, no Rainbow)

> Goal: a signed credit is arithmetically sound and actually gated by the controls the
> methodology claims. All fixable with our own code.

### P1.a — Net-credit floor; never sign a negative credit  · size S
- **Problem:** `step8_net_credit` (lca_engine.py:212) has no `max(0, …)`; a negative
  `net_credit_t_co2e` is signed and persisted as issuable (demonstrated: −0.10 t).
- **Fix:** clamp at the engine boundary **and** make `recompute_batch_credit` treat a
  pre-clamp negative as a hard provisional reason (`net_credit_nonpositive`) rather than
  silently flooring to 0 — surfacing *why* is the honest behavior. Decide product rule:
  negative → provisional + reason, never signed.
- **Tests:** property test over input ranges asserting `net ≥ 0` on any signed row; the
  exact demonstrated negative case asserts `provisional=True` + reason present + no
  signature.
- **DoD:** no signed batch can carry `net_credit_t_co2e < 0`.

### P1.b — Batch → project linkage (schema, additive)  · size M · unblocks P1.c
- **Problem:** C8/C9 gates need a batch's project (for scale-calibration and annual-
  verification lookup); no linkage column exists, so the gates can't be wired.
- **Fix:** additive migration adding nullable `project_id` FK on `batches`; backfill path
  for existing rows (nullable → gate treats null as "unknown" = provisional, never crash).
  API: accept/derive project on batch creation.
- **Tests:** migration round-trip on Postgres (P0.c); a batch with/without project resolves
  the linkage; null project yields a provisional reason, not an exception.
- **DoD:** linkage present, nullable-safe, round-trips on Postgres.

### P1.c — Wire the dormant C8/C9/PAH gates into issuance  · size M · depends P1.b
- **Problem:** `derive_scale_calibration_compliance` and `derive_annual_methane_compliance`
  are shipped but **never called** in `recompute_batch_credit`; `derive_pah_compliance` is
  called with hardcoded `enforced=False`. The advertised C10 gate is partially dormant.
- **Refactor first (same PR or immediately prior):** extract a single
  `assemble_issuance_gates(batch, evidence, project) -> reasons[]` that runs *all* derivers
  through one list, so no gate can be forgotten again. `recompute_batch_credit` calls only
  this. This is the structural fix that prevents recurrence.
- **Fix (plumbing PR):** route scale-calibration + annual-methane + PAH derivers through
  the assembler, still `enforced=False` (behavior unchanged — pure wiring, provable no-op).
- **Fix (enforcement PR, separate, one-gate-one-commit):** flip each gate's flag ON, one
  commit per gate, behind a config flag.
- **Tests:** a closed-kiln batch missing scale-cal / missing ≥3 methane runs / missing PAH
  each stays provisional with the correct reason; a fully-compliant batch clears. Add the
  "wiring is a no-op" test (reasons identical before/after the plumbing PR with flags off).
- **DoD:** every methodology control the code claims to enforce is invoked on the signing
  path; flips are individually revertible.

### P1.d — Decimal money-math + backend-independent signature  · size M
- **Problem:** `net_credit_t_co2e` and the LCA math are binary `Float`; the HMAC signs
  `json.dumps(float)`, so SQLite-vs-Postgres float serialization can drift the signature.
- **Fix:** use `Decimal` (fixed scale, `ROUND_HALF_EVEN`) for money-adjacent values;
  canonicalize the signed payload to a deterministic decimal-string representation
  independent of DB float rounding. Column type migration `Float → Numeric(precision,scale)`
  (additive-safe, round-tripped on Postgres).
- **Tests:** signature is byte-identical for the same logical inputs computed on SQLite and
  Postgres (`@pg`); rounding is deterministic; golden signature vector locked.
- **DoD:** identical credit → identical signature across both backends.

---

## 5. Phase 2 — Security hardening (no Rainbow, mostly middleware/startup)

### P2.a — Secret strength floor at startup  · size S
- Enforce min length (≥32 bytes) + charset/format (base64 or hex) for `DMRV_HMAC_SECRET` /
  `DMRV_ADMIN_SECRET` in `load_settings()`; refuse weak secrets loudly. Builds on P0.a.
- **Tests:** startup raises on short/weak secret; passes on a strong one.

### P2.b — Rate limiting  · size M
- Add `slowapi` (or ASGI middleware): strict per-IP + per-device throttle on `/admin/*`
  and `/register`; looser global cap on evidence endpoints. Return `429 + Retry-After`.
- **Tests:** N+1th request within window → 429; admin brute-force path throttled.

### P2.c — Enforce body-size limit under chunked encoding  · size S
- **Problem:** the `Content-Length` check (server.py:224) is bypassable via
  `Transfer-Encoding: chunked` → OOM DoS on JSON routes.
- **Fix:** cap accumulated bytes in an ASGI `receive` wrapper regardless of headers
  (the media path already streams; apply the same discipline to JSON).
- **Tests:** a chunked request exceeding the cap is rejected with 413 before buffering.

### P2.d — Validate Ed25519 public key at registration  · size S
- Attempt `Ed25519PublicKey.from_public_bytes(decode(key))` at `/register`; `400` on
  invalid, so bogus keys never persist to fail later.
- **Tests:** malformed key → 400; valid key → 201.

### P2.e — Replay window (timestamp + nonce)  · size L · coordinated client+server
- **Problem:** replay is defeated only by DB idempotency dedup, not the signature; a
  captured signed request is valid forever.
- **Fix:** add `X-Timestamp` to the signed canonical (versioned canonical — bump a
  canonical-version header so old/new clients interoperate during rollout); reject outside
  ±N minutes; add a short-TTL nonce/idempotency-key store to reject exact replays.
  **Requires the client `CryptoSigner` change too** — ship server accepting both canonical
  versions first, then migrate clients, then retire v1. Sequence carefully.
- **Tests:** stale timestamp rejected; replayed nonce rejected; both canonical versions
  verify during the migration window.

---

## 6. Phase 3 — Data integrity at scale (no Rainbow; Postgres-only bugs)

### P3.a — Serialize `recompute_batch_credit` against concurrent evidence  · size M
- **Problem:** read-modify-write with no lock; two concurrent uploads can compute a stale
  credit and leave a batch **permanently provisional**. Invisible on SQLite.
- **Fix:** `SELECT … FOR UPDATE` on the batch row (Postgres) around recompute; ensure the
  evidence insert + batch update commit in **one transaction**; make recompute idempotent.
- **Tests (`@pg`):** two concurrent evidence writers on one batch converge to the correct
  final credit; no lost update; batch not stuck provisional.

### P3.b — Foreign keys + `batch_uuid` type consistency  · size M
- **Problem:** evidence tables store `batch_uuid` as `String(36)` with **no FK** to
  `batches` (`UUID`) → orphans, no referential integrity.
- **Fix:** additive migration adding FK constraints (evidence-first flow preserved: FK
  `ON DELETE` policy chosen so pre-batch evidence is still legal per the ownership model);
  normalize type. Add an orphan-detection query for cleanup.
- **Tests (`@pg`):** FK enforced; evidence-first upload still legal; orphan query correct.

### P3.c — File/DB atomicity, retention, and pluggable storage  · size L
- **Problem:** file written before DB commit; local-disk only (no horizontal scale); no
  retention/cleanup → disk fill + orphans.
- **Fix:** write to temp → commit row → atomic rename+fsync; startup + periodic orphan
  reaper (age-based); introduce a `StorageBackend` interface (local impl now, S3/GCS impl
  as a drop-in later — interface only, no cloud dependency added yet).
- **Tests:** crash-between-write-and-commit leaves no dangling row; reaper removes only
  true orphans; storage interface has a local + fake backend test.

### P3.d — Evidence idempotency hardening  · size M
- Persist the client idempotency key on evidence rows; unique constraint; duplicate-media
  re-POST is a safe no-op (dedup by declared hash). Closes the under-tested retry paths.
- **Tests:** identical retry → single row + 2xx; duplicate media hash → deduped; the
  `@pg` concurrent-retry case.

---

## 7. Phase 4 — Client (Flutter) robustness (no Rainbow)

### P4.a — Sanitize BLE readings at the parser boundary  · size S
- Reject `NaN`/`Inf`/negative/out-of-range temp & weight at the service edge before they
  reach the log/outbox (a garbage reading currently serializes and wedges the batch in
  PENDING on server JSON reject).
- **Tests:** garbage bytes → dropped + surfaced, never appended; valid range accepted.

### P4.b — Outbox poison-message recovery  · size M
- **Problem:** items exceeding retry cap become `FAILED_PERMANENTLY` and are silently
  buried while the UI shows "synced." Silent field-data loss.
- **Fix (engine + minimal surface):** never report "all synced" when failed items exist;
  expose a failed-items list with a manual retry + a diagnostic reason. Distinguish
  transient (retry) vs permanent (4xx) with backoff at the loop level.
- **Tests:** a permanently-rejected item is visible and manually retryable; sync-complete
  state is false while failures exist.

### P4.c — Server-side drying-mandate enforcement  · size M · pairs with backend
- **Problem:** the 72-hour drying lock is client-side only and **unverifiable on iOS**
  (spoofable by changing the clock).
- **Fix:** server rejects/flags-provisional harvest timestamps failing the 72h rule using
  server-trusted time; the client check becomes advisory UX only. (Backend deriver +
  provisional reason; additive, flag-gated flip.)
- **Tests:** server marks provisional when the drying interval is unmet regardless of
  client claims; client no longer the source of truth.

### P4.d — Self-service key rotation / re-enrollment  · size M · depends P2.e store
- Add a re-enrollment endpoint that accepts proof-of-possession of the old key (or an admin
  re-enroll), so a wiped/reinstalled device isn't permanently locked out.
- **Tests:** rotate → old signatures rejected, new accepted; lockout path recoverable.

### P4.e — Real device attestation  · size L · no Rainbow, but external config
- **Problem:** `_ATTESTATION_ENFORCED=False`; forged blobs pass. Every credit rests on
  unverified device integrity.
- **Fix:** integrate Google Play Integrity + Apple DeviceCheck/App Attest server-side
  verification; flip `_ATTESTATION_ENFORCED=True` behind a flag once field devices are
  provisioned. Needs Google/Apple project config (not Rainbow), so sequence late.
- **Tests:** forged/absent attestation → provisional (or reject per policy); genuine
  attestation → passes; flag-off path unchanged.

---

## 8. Phase 5 — Deployability & ops (no Rainbow)  ·  Phase 6 — Mobile release

### P5.a — Containerize  · size M
- Multi-stage `Dockerfile` (backend) + `docker-compose.yml` (api + postgres) for parity;
  gunicorn/uvicorn worker config (`2·cores+1`), `uvloop`/`httptools` added to
  `requirements.txt`. Documented run command replaces the ad-hoc one.
- **Tests:** compose up → health green → a smoke request succeeds (can run in CI).

### P5.b — Engine pool, timeouts, graceful shutdown  · size S
- `create_async_engine(..., pool_size, max_overflow, pool_pre_ping=True, pool_timeout)`;
  request-timeout middleware (60s JSON / 300s media); lifespan closes the engine and drains
  on SIGTERM.
- **Tests:** pool exhaustion returns 503 not hang; shutdown drains in-flight request.

### P5.c — Real health/readiness + observability  · size M
- `/api/health` executes `SELECT 1`; add `/api/ready` (200 only after migrations); JSON
  structured logging with a request-id middleware (emit `request_id`, `device_id`,
  `batch_uuid`); optional Prometheus instrumentation.
- **Tests:** health fails when DB down; ready false pre-migration; logs carry request-id.

### P5.d — Startup config validation & `.env.example`  · size S
- In `load_settings()`: reject `localhost`/`example.com` when `DMRV_ENV=prod`; validate
  `DATABASE_URL` shape; ship a complete `.env.example` (no secrets). Echo non-secret config
  at boot.
- **Tests:** prod env with placeholder origin refuses to start.

### P5.e — Backup & object-storage runbook  · size S (doc + adapter)
- Document pg backup (pg_dump/WAL) + RPO/RTO; wire the P3.c `StorageBackend` S3 adapter for
  evidence durability. (Adapter code no-Rainbow; provisioning is an ops task.)

### P6.a — Android release signing & release hygiene  · size M · independent, start anytime
- **Problem:** release build signed with the **debug key** (build.gradle.kts:37) → Play
  Store rejects. Generic `applicationId`; no ProGuard/R8.
- **Fix:** release keystore + `signingConfigs.release` sourced from CI secrets; per-client
  `applicationId`; `proguard-rules.pro` (keep crypto/Flutter/BLE); version-bump process;
  CI builds a signed AAB.
- **Tests:** CI produces an installable signed AAB; obfuscated build passes smoke.

---

## 9. Explicitly OUT of scope (Rainbow-blocked — do NOT attempt without them)

- **Real transport/fuel emission factors** (`emission_factors.py` `TODO(cite)`,
  `TRANSPORT_EVENTS_ENFORCED=False`). Requires methodology-sourced factors from Rainbow.
  *Plumbing* (P3, enforcement flag) can be prepared, but the flip stays OFF until numbers
  arrive.
- **Any methodology threshold/parameter value** not already in the repo (e.g. definitive
  leakage/PAH limits, GHG quantification constants). Wire the gate; supply the value later.
- **The GHG quantification document itself** (meeting item #1). No credit-magnitude claim
  is final without it.

> These do not block a **supervised pilot** (controlled devices, manual credit review), but
> they **do** block issuing sellable credits. Keep the enforcement flags OFF and label
> pilot credits provisional until Rainbow closes these.

---

## 10. Suggested execution cadence

| Milestone | Items | Unlocks |
|---|---|---|
| **M0 — Safety net** | P0.a, P0.b, P0.c | All later work is auto-verified on Postgres |
| **M1 — Trustworthy credit** | P1.a → P1.d | Credits are sound + fully gated (flags ready) |
| **M2 — Hardened** | P2.a–P2.e | Public-internet-safe API |
| **M3 — Scale-safe** | P3.a–P3.d | Survives concurrency + real data volume |
| **M4 — Field-robust** | P4.a–P4.e | Survives real devices/networks |
| **M5 — Deployable** | P5.a–P5.e | Can actually run in prod |
| **M6 — Releasable** | P6.a | App can ship to Play Store |

Within a milestone, independent items parallelize; across milestones, respect the critical
paths in §2. Each item is one PR, test-first, meeting the §1 DoD. Start at **P0.a**.
