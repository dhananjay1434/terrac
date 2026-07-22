# TerraCipher dMRV — Production Execution Plan (phase-by-phase, code-exact)

**What this is.** The single executable build plan that takes us from *end-of-planning*
to *production-ready*. It turns `PRODUCT_BLUEPRINT.md` (the *what*) and
`BOUNDARY_DESIGN.md` (the *how* for boundaries) into an ordered sequence of small,
test-gated, non-breaking phases with **exact file paths, migration chaining, test
files, and Definition-of-Done gates**.

**How to use it.** Execute one **Part** per session/PR. Do not start a Part until the
previous Part's DoD is green. Each Part is written so an engineer (or an agent) can
execute it without re-deriving anything. Read `§0 Engineering Constitution` first — it
is binding on every Part and overrides convenience.

**State this plan was written against (verify before starting — see `§Verify`):**
- Alembic HEAD revision: **`d6e7f8a9bac1`** (`media_add_capture_type`).
- Drift schema version: **v25** (`lib/data/local/app_database.dart:68`).
- Sync routing maps: `kEndpointByTable` / `kCaptureTypeByTable`
  (`lib/services/sync_queue_manager.dart:52,73`).
- Corroboration entry point: `_evaluate_anchor` (`backend/geo.py:92`).
- Backend suite: ~455 tests green. Flutter suite: ~253 tests green.

---

## §0. Engineering Constitution (BINDING on every Part)

These are not guidelines. A PR that violates any of them is rejected regardless of
whether it "works". Write code the way a principal engineer who must maintain this for
five years would demand.

### 0.1 Non-negotiable invariants (the moat — never weaken)
1. **Encrypted at rest.** All new persisted PII/evidence rides SQLCipher on-device.
   No new plaintext store, no new SharedPreferences for anything sensitive.
2. **Signed + hash-anchored evidence.** Every new evidence artifact (photo, video,
   PDF, weigh-ticket, consent) is SHA-256 hashed and Ed25519-signed via the existing
   `crypto_signer.dart` → verified in `security.py`. No unsigned evidence path is ever
   introduced.
3. **Two-phase, hash-verified sync.** New evidence uses `insert*WithOutbox` +
   `SyncOutbox`. Never bypass the outbox. Never delete a local artifact before
   `server_sha256` is confirmed.
4. **Transparent server-side credit math.** Credits/LCA stay computed server-side and
   auditable. No client-trusted credit inputs.
5. **Never fabricate.** No stub that reports data it did not capture (this plan *kills*
   the existing boundary boolean; it must not create new ones). Missing data renders as
   missing, everywhere.

### 0.2 Architecture discipline (modularity / scalability)
1. **Reuse the rails; do not reinvent.** New backend evidence endpoint → the
   `evidence.py` pattern (verify signature → `_assert_batch_ownership` → persist →
   recompute). New portal action → `require_role`. New capture → `SecureCaptureService`.
   New sync route → add to `kEndpointByTable`/`kCaptureTypeByTable`, do not fork the
   sync manager.
2. **One module = one responsibility.** No new "god file". Geometry math lives in a new
   `backend/geometry.py`, not inside `routers/`. Signing lives in `crypto_signer` /
   `security.py`, not copied inline. If a function exceeds ~40 lines or mixes I/O with
   pure logic, split it — pure logic must be unit-testable without a DB or network.
3. **Pure core, thin edges.** Business rules (overlap %, area, state-machine
   transitions, mass-from-density) are **pure functions** taking plain inputs and
   returning plain results. Routers/screens are thin adapters that call them. This is
   what makes it testable and scalable; enforce it.
4. **Config over code.** New tunables (tolerances, thresholds, feature toggles) are
   env-gated settings in `settings.py` (default-on for gates), never magic numbers
   inlined at call sites. Mirror `DMRV_REQUIRE_EXIF_GPS`.
5. **Schemas at the boundary.** Every new endpoint has explicit Pydantic request/
   response schemas in `schemas.py` / `portal/schemas.py`. No `dict[str, Any]` passing
   through the API surface. Portal gets matching TS types in `api.ts`.
6. **Layering, enforced.** App: `ui/screens` → `providers` (Riverpod notifiers) →
   `data`/`services`. Screens never touch Drift or `http` directly. Backend:
   `routers` → `services`/domain modules → `models`. No cross-layer shortcuts.
7. **No dead scaffolding.** Do not commit commented-out code, `print`/`debugPrint`
   debugging, TODO-without-ticket, or "temporary" flags. If it is temporary, it does
   not get committed.
8. **Naming + symmetry.** New code reads like the code next to it: same naming, same
   error handling, same test layout. A reviewer should not be able to tell which files
   are new by style alone.

### 0.3 Non-breaking discipline (never regress a shipped device)
1. **Additive migrations only.** New columns are **nullable** (or have a server
   default). Existing rows must remain valid. Every Alembic migration chains from the
   current HEAD and has a real, tested `downgrade()`. Every Drift bump adds a numbered
   `MigrationStrategy` step and a migration test.
2. **Grandfather old data.** A batch/farmer/parcel created before a feature exists must
   still read, sync, and corroborate. New gates skip gracefully when their referenced
   data is absent (e.g. no `parcel_uuid` → skip point-in-polygon, don't fail).
3. **Backward-compatible payloads.** Never add a required field to a *signed* JSON body
   consumed by existing app versions (this is the exact bug that caused the V4b 422
   `extra_forbidden` regression — capture_type went in the signed body). New optional
   fields only; strict endpoints must still accept old payloads.
4. **Env-gated rollout.** Every new compliance/anti-fraud gate ships behind its own
   `settings.py` flag, default-on in prod, but flip-off-able for demo without a code
   change.
5. **No lockstep deploy assumption.** Backend must serve both the old and new app for
   the overlap window. Old app + new backend = green. New app + old backend = degrades
   gracefully, never crashes.

### 0.4 Test discipline (the gate, per Part)
1. **Test-first for pure logic.** Overlap, area, state transitions, mass math, config
   selection — write the unit test before the implementation.
2. **Three layers, every Part that spans them:** backend `pytest`, app `flutter test`,
   portal `vitest` + `tsc --noEmit` + `vite build`.
3. **Cover: happy path, boundary/edge, failure, env-gate-off, and back-compat
   (grandfathered old row).** A Part with no back-compat test does not pass DoD.
4. **No flakiness, no network in unit tests.** Pure functions tested in isolation;
   integration tests use the existing `conftest.py` fixtures.
5. **Green-to-green.** Full relevant suite green *before* the Part and *after*. Never
   commit red. One phase = one commit. Do **not** push unless the user asks.

### 0.5 Per-Part workflow (do this every time)
1. Re-read the `§Verify` anchors; confirm HEAD revision + Drift version unchanged.
2. Write/extend the failing tests (0.4.1).
3. Implement in the smallest modular slices (0.2).
4. Run the three suites (0.4.2). Fix to green.
5. Run `/code-review` (or self-review) against `§0` — reject your own violations.
6. Update the relevant runbook doc + this plan's checkboxes.
7. One commit, conventional message, scoped. Do not push unless asked.

### 0.6 Definition of "Production-Ready" (the finish line — `§7`)
All Parts 0–4 done + `§7` production checklist green. Part 5 (scale) is post-launch.

### 0.7 Cross-cutting requirements (apply to EVERY Part — audit-added)
These were missing from the first draft and are now binding. A Part that touches the
relevant surface but skips these fails DoD.

1. **Concurrency safety.** Any check-then-write that enforces an invariant across rows
   (parcel overlap, mobile-number uniqueness, dispatch state transition) must be
   **serialized at the DB layer** — a transactional `SELECT … FOR UPDATE` on the
   scoping row (e.g. the `project`), a Postgres advisory lock, or a unique constraint —
   never a bare read-then-insert. Add a concurrent-writers test.
2. **Idempotent sync.** Every new evidence entity uses a **client-generated UUID** as
   its PK (`parcel_uuid`, `farmer_uuid`, `dispatch_uuid`) and the endpoint does
   **upsert-on-conflict** (retry-safe), because the outbox retries. State this per
   entity; test a duplicate submission is a no-op, not a second row.
3. **Input-complexity guards (DoS).** The existing Content-Length cap + rate-limit
   (`middleware.py`) bound bytes and frequency, not *content complexity*. Any endpoint
   that runs non-trivial compute on user input (geometry especially) must cap the work:
   **vertex count**, coordinate-range/finiteness, ring count — reject before the
   expensive op. Add a pathological-input test.
4. **Observability per gate.** Every new compliance/anti-fraud gate and quarantine
   state emits a **prometheus metric + structured log** (reuse `observability.py`;
   sentry breadcrumb for rejections). We must be able to see, in prod, how often
   `QUARANTINE_GPS_OUTSIDE_PARCEL`, overlap-reject, kill-switch, and min-version-block
   fire. A silent gate is an unshippable gate.
5. **Staged rollout, not deploy-flip.** Gates are default-on in **code + tests**, but
   rolled out to the live fleet via the remote control plane (0.4) **starting OFF →
   canary → observe metrics (F4) → enable**. Never enable a new quarantine gate on a
   deployed fleet at deploy time — it can mass-quarantine legitimate in-flight data.
   Document the enable-order in each Part's runbook.
6. **PII lifecycle (any Part touching personal data — B especially).** Beyond
   minimize+encrypt+sign: define **retention** (how long), **erasure** (data-subject
   deletion path that also tombstones synced copies), and a **PII-access audit log**
   (who viewed KYC/consent in the portal). Align to India DPDP Act + registry audit
   needs. No PII feature ships without these three.
7. **UI parity for every new screen/page.** New **app** screens ship en+hi strings
   (`app_en.arb`/`app_hi.arb`) — not just Part J. New **portal** pages: (a) join the
   jest-axe suite (`portal/src/__tests__/a11y.test.tsx`) with zero violations, and
   (b) any growable list uses the **existing cursor-pagination pattern** (V4, Batches
   table) — never load-all.
8. **Contract stability.** Extend the existing contract tests
   (`test_client_contract.py`, `test_endpoint_schemas.py`) for every new/changed
   endpoint so old-app/new-backend compatibility is machine-checked, not asserted by
   hand.
9. **Branch + review flow.** One **feature branch per Part** (`feat/part-0-project`,
   …), one commit per sub-part, `/code-review` + (for auth/PII/crypto Parts)
   `/security-review` before merge. Do not push or open PRs unless the user asks.

---

## §1. Dependency graph & sequencing

```
PART 0  Foundations (must be first — everything hangs off these)
  0.1 Server Ed25519 signing key + kid rotation   ← used by A(field-walk) + I(config)
  0.2 Project entity + backfill                    ← unblocks A,B,C,D,G
  0.3 Kill the boundary fake stub                  ← credibility; independent
  0.4 Remote control plane (flags/kill/min-ver)    ← ops safety before wider deploy
        │
PART 1  A — Source-parcel boundary + overlap + point-in-polygon   (needs 0.1,0.2,0.3)
PART 2  B — Farmer registry + KYC + FPIC consent + payments        (needs 0.2)
PART 3  C — Facility + Dispatch custody state machine + dual weigh  (needs 0.2)
PART 4  Compete pack (parallelizable): O,E,F,H,M,J,K,G             (mostly needs 0.2/C)
PART 5  Scale (post-launch): D,L,N + A-phase2 field-walk + PostGIS
```

Rule: **at most one L-effort workstream in flight** unless staffed by parallel
engineers. Parts 1→2→3 are sequential (each is an L). Part 4 items are S/M and may
parallelize once their dependency exists.

---

## PART 0 — Foundations

> Goal: put the load-bearing primitives in place so no later Part hangs off an
> un-scoped string, an unsigned server payload, or a fabricated boolean. Four small,
> independent sub-parts; each is its own commit.

### 0.1 — Server Ed25519 signing keypair + `kid` rotation  · P0 · S

**Why.** Both A (signed field-walk link) and I (signed remote config) need the
*server* to sign and the *app* to verify (opposite direction from device signing).
Build the key management **once**; both reuse it. Doing it now prevents two ad-hoc
key implementations later.

**Backend — create (new module, single responsibility):**
- `backend/server_signing.py` (NEW) — pure-ish module: load server private key from
  env (`DMRV_SERVER_SIGNING_SK`, base64), expose `sign(payload: bytes) -> (sig, kid)`
  and `public_keys() -> dict[kid, pubkey]`. Support **N keys** keyed by `kid` for
  rotation (verify against any known key; sign with the current one).
- `backend/settings.py` (EDIT) — add `DMRV_SERVER_SIGNING_SK`,
  `DMRV_SERVER_SIGNING_KID`, `DMRV_SERVER_SIGNING_PUBKEYS` (json map for verify/
  rotation). Fail-loud only when a feature that needs signing is enabled.
- `backend/routers/health.py` or a new `GET /api/v1/pubkeys` (EDIT/NEW) — expose the
  public keys + current `kid` so the app can pin/refresh.

**App — create:**
- `lib/services/server_signature_verifier.dart` (NEW) — verify an Ed25519 signature
  from the server given a `kid`; hold a small pinned keyset (bootstrapped from build
  config, refreshable from `/pubkeys`). Pure verify, no I/O beyond the keystore.

**Key management runbook (write it, don't hand-wave — audit-added):**
- **Generation** offline (never on a dev box that logs); store the **private key only**
  in Render's secret env (`DMRV_SERVER_SIGNING_SK`), never in git, never in the image.
- **`kid` rotation:** new key added to `DMRV_SERVER_SIGNING_PUBKEYS` (verify set)
  *before* it becomes the signer (`DMRV_SERVER_SIGNING_KID`) — so the app can verify
  the new `kid` before it's used. Old `kid` stays in the verify set until every
  cached/issued artifact using it has expired. Document the overlap window.
- **Blast radius:** signatures are over short-lived config/links (not stored evidence),
  so rotation does not invalidate the audit trail — state this explicitly so no one
  fears rotating. Write the runbook to `docs/SERVER_SIGNING_KEY.md`.

**Tests (create):**
- `backend/tests/test_server_signing.py` (NEW): sign→verify round-trip; wrong key
  fails; unknown `kid` rejected; rotation (old `kid` still verifies; new `kid` in
  verify set before it signs).
- `test/server_signature_verifier_test.dart` (NEW): valid sig accepted; tampered
  payload rejected; unknown `kid` rejected.

**DoD.** Both suites green. No feature enables it yet (dormant, safe). Key material is
env-only; nothing secret committed.

**Non-breaking note.** Purely additive; no existing path changes.

---

### 0.2 — `Project` entity + backfill  · P0 · S

**Why.** `project_id` is a bare `String(128)` on `Batch` (`models.py:333`) and
`AnnualVerification` (`models.py:266`) — no table, no metadata, no tenancy anchor.
A/B/C/D/G all scope off "project". Build the real entity first; keep the string as the
natural join key so **existing batches don't break**.

**Backend:**
- `backend/models.py` (EDIT) — add `Project`:
  `project_id (String(128) PK — same natural key existing rows already use),
  name, registry_config_id (nullable → G), org_id (nullable → D),
  status ('active'|'closed', default 'active'), created_at`.
  Do **not** rename or retype the existing `Batch.project_id` — add a relationship by
  value (FK-by-value) so no data rewrite is needed.
- `backend/alembic/versions/` (NEW migration, chain from HEAD `d6e7f8a9bac1`):
  `alembic revision -m "create_project_table_and_backfill"`.
  - `upgrade()`: create `project`; **backfill** one row per distinct existing
    `Batch.project_id` and `AnnualVerification.project_id` (idempotent INSERT … SELECT
    DISTINCT … WHERE NOT EXISTS). Then add the FK constraint (nullable-safe / deferred)
    only after backfill so nothing orphans.
  - `downgrade()`: drop FK, drop table. Tested.
- `backend/portal/routes.py` (EDIT) — `GET /api/v1/portal/projects` (list) +
  `POST /api/v1/portal/projects` (create), both `require_role("admin")`.
- `backend/portal/schemas.py` (EDIT) — `ProjectCreate`, `ProjectOut`.

**Portal:**
- `portal/src/pages/Registry.tsx` (EDIT) or `portal/src/pages/Projects.tsx` (NEW,
  preferred — keep Registry focused) — minimal admin: list + create project.
- `portal/src/api.ts` (EDIT) — `listProjects`, `createProject` + TS types.

**Tests (create/extend):**
- `backend/tests/test_project_entity.py` (NEW): create; list role-gated; batch and
  annual-verification resolve their project; **backfill covers all existing distinct
  `project_id`s with zero orphans** (this is the critical back-compat test); re-run
  migration is idempotent.
- Extend `backend/tests/test_batch_project_linkage.py` (existing) — assert the linkage
  now resolves to a real `Project` row.
- `portal/src/pages/__tests__/Projects.test.tsx` (NEW): create + list render; role gate.

**DoD.** All three suites green; existing `test_batch_project_linkage.py` +
`test_project_registry_c8.py` still green (regression); backfill test proves no orphan.

**Non-breaking note.** Existing `project_id` strings are preserved as the PK/join key;
the migration only *adds* a table and seeds it. Old app unaffected (it never sends a
Project object).

---

### 0.3 — Kill the boundary fake stub  · P0 · S (credibility; independent)

**Why.** `captureGpsPolygon()` persists a boolean and the UI renders a fabricated
`'Polygon captured // 4 vertices'` (`lantana_sourcing_screen.dart:349-350`,
`lantana_sourcing_notifier.dart:209-213`). This is a **false attestation** — it claims
captured geometry that never existed. It must go *before* we ship anything else. (The
real boundary arrives in Part 1; this sub-part removes the lie and leaves an honest
"no parcel yet" state.)

**App — remove, don't hide:**
- `lib/providers/lantana_sourcing_notifier.dart` (EDIT) — delete `polygonCaptured`
  state field (l.25,42,96,111,131-137), `_persistPolygon` (l.162-164),
  `captureGpsPolygon` (l.209-213), and the `polygon_captured` SharedPreferences key.
- `lib/ui/screens/lantana_sourcing_screen.dart` (EDIT) — delete `_PolygonBlock`
  (l.304-350) and its usage (l.73-76). Replace with an honest read-only placeholder:
  "Source parcel: not yet assigned" (wired to real `parcel_uuid` in Part 1). No fake
  vertex count, ever.
- `lib/data/local/tables.dart` (EDIT) — if any polygon boolean column exists, remove
  it via the Drift bump below (or in Part 1 if it's cleaner to batch — but the *UI/
  notifier lie* is removed now regardless).

**Tests (extend):**
- `test/lantana_sourcing_notifier_test.dart` (EXTEND) — **regression guard**:
  `captureGpsPolygon` no longer exists / no boolean is persisted; screen shows the
  honest "not yet assigned" state.

**DoD.** Flutter suite green; no code path writes a boundary boolean; grep for
`polygon_captured` / `captureGpsPolygon` / `4 vertices` returns nothing.

**Non-breaking note.** Removes fabricated state only; no server contract changes. If a
Drift column is dropped, ship it as the v25→v26 step (or defer the column drop to Part 1
and only remove the UI/notifier now — dropping a column is the riskier half).

---

### 0.4 — Remote control plane: signed flags + kill-switch + min-version · P0 · M

**Why.** Private-APK + CI-off = **zero remote control of a deployed fleet**. A bad
build or discovered fraud vector cannot be flag-gated or force-updated. This is ops
safety and must exist before wider field deployment. Uses 0.1's server key — **no
Firebase needed** (a signed boot-time config suffices).

**Backend:**
- `backend/routers/` → new `config.py` (NEW) — `GET /api/v1/config` returns an
  **Ed25519-signed** JSON: `{ flags: {...}, min_version, kill_switch, message,
  signed_at, kid, signature }`, signed via `server_signing.py` (0.1).
- `backend/portal/routes.py` (EDIT) — admin endpoints to edit flags/min-version/
  kill-switch (`require_role("admin")`), persisted in a small `app_config` table.
- `backend/models.py` + migration (NEW, chain from 0.2's revision) — `app_config`
  (single-row or key/value).
- `backend/portal/schemas.py` (EDIT) — config schemas.

**App:**
- `lib/services/remote_config_service.dart` (NEW) — fetch `/config` at boot, **verify
  offline** with `server_signature_verifier.dart` (0.1), cache to SQLCipher, expose a
  typed `RemoteConfig`. Enforce: below `min_version` → hard "update required" screen;
  `kill_switch` → disable capture/sync with a message. Fail-safe: if unreachable, use
  last cached signed config (never fail open on kill-switch).
- `lib/providers/` (NEW notifier) + a gate in app bootstrap.

**Portal:** flags admin UI (small) under Projects/Registry, `require_role("admin")`.

**Tests (create):**
- `backend/tests/test_remote_config.py` (NEW): config is signed; admin edits persist;
  role-gated; schema stable.
- `test/remote_config_service_test.dart` (NEW): tampered config rejected; below
  min-version blocks; kill-switch disables; **unreachable → last cached config used**
  (fail-safe, back-compat).

**DoD.** Three suites green. Default flags = current behavior (no silent change).

**Non-breaking note.** Additive endpoint + table. Old app ignores `/config` (doesn't
call it) and keeps working; new app degrades safely if backend lacks the endpoint.

**Part 0 exit gate:** backend + flutter + portal suites fully green; §0 self-review
clean; four commits (0.1–0.4). No push unless asked.

---

## PART 1 — A: Source-parcel boundary + overlap + corroboration · P0 · L

> Depends on 0.1 (field-walk sign, phase-2), 0.2 (Project), 0.3 (stub gone).
> Full geometry spec: `docs/BOUNDARY_DESIGN.md`. Build order mirrors that doc.

### 1.1 — Geometry core (pure module, test-first)
- `backend/geometry.py` (NEW) — **pure functions only**, no DB/HTTP:
  `parse_geojson`, `validate_polygon` (shapely `is_valid`/`make_valid`, ≥3 vertices),
  `guard_complexity` (**DoS guard, audit-added** — reject before any geometry op if
  vertices > `DMRV_PARCEL_MAX_VERTICES`, rings > cap, or any coord non-finite /
  out-of-range lat∈[-90,90] lon∈[-180,180]), `geodesic_area_m2`
  (`pyproj.Geod.geometry_area_perimeter`), `bbox_of`, `overlap_ratio(a, b)`
  (projected-meters intersection/area with **absolute sliver floor ~200 m² + ratio
  ~2%**), `point_in_polygon(poly, lon, lat, buffer_m)`.
- `backend/requirements.txt` (EDIT) — add **pinned** `shapely==<x>`, `pyproj==<x>`
  (both ship cp311 manylinux wheels → install on `python:3.11-slim` with no apt deps;
  verify the Docker build + note the image-size delta). No PostGIS for MVP.
- `backend/settings.py` (EDIT) — `DMRV_PARCEL_OVERLAP_ENFORCED` (default on),
  `DMRV_PARCEL_OVERLAP_RATIO`, `DMRV_PARCEL_SLIVER_FLOOR_M2`,
  `DMRV_PARCEL_GEOFENCE_BUFFER_M`, `DMRV_PARCEL_AREA_MISMATCH_PCT`,
  `DMRV_PARCEL_MAX_VERTICES`.
- **Test-first:** `backend/tests/test_geometry.py` (NEW) — area of a known square;
  overlap accept/reject; sliver floor prevents false-reject of adjacent parcels;
  self-intersecting → invalid; point inside/outside/buffer-edge; **pathological input
  (vertex bomb / NaN / out-of-range coord) rejected by `guard_complexity` before any
  shapely call**. Written **before** the endpoint.

### 1.2 — Data model + migration
- `backend/models.py` (EDIT) — `SourceParcel` (per `BOUNDARY_DESIGN.md §2`:
  `parcel_uuid PK, project_id FK→project, name, boundary_geojson TEXT, area_m2,
  declared_area_acres, bbox_min/max_lat/lon, boundary_method, boundary_status,
  created_by_user_id, created_at`) + `Batch.parcel_uuid` (**nullable**, grandfather).
- Migration (NEW, chain from Part 0 HEAD): create `source_parcel`; add nullable
  `batch.parcel_uuid`; indexes on `project_id` + bbox columns. Real `downgrade()`.

### 1.3 — Registration endpoint (thin adapter over geometry core)
- `backend/portal/routes.py` (EDIT) — `POST /api/v1/portal/parcels`
  (`require_role("admin")`): `guard_complexity` → validity → area → **bbox-prefilter
  approved parcels (SQL) → exact overlap only on candidates** → store `approved` /
  reject with reason (`boundary_invalid` | `area_mismatch` |
  `boundary_overlaps_existing_parcel`). `GET /parcels?project_id=` (**cursor-paginated**,
  reuse the V4 pattern).
  - **Concurrency (audit-added, CRITICAL):** the overlap check + insert run in **one
    transaction that first takes a lock scoped to the project** (`SELECT … FOR UPDATE`
    on the `project` row, or a Postgres advisory lock keyed by `project_id`) so two
    simultaneous registrations cannot both pass the overlap check. Without this the
    anti-double-count guarantee is void. Add a concurrent-writers test.
  - **Idempotency:** client-supplied `parcel_uuid` PK + upsert-on-conflict (retry-safe).
  - **Observability:** emit a metric/structured log on every accept + each reject reason.
- `backend/portal/schemas.py` (EDIT) — `ParcelCreate`, `ParcelOut`, rejection reason.

### 1.4 — Corroboration (extend, don't fork)
- `backend/geo.py` (EDIT `_evaluate_anchor`, l.92) — **if** batch has `parcel_uuid`,
  load polygon and check `point_in_polygon(buffer=DMRV_PARCEL_GEOFENCE_BUFFER_M)`;
  outside → new status `QUARANTINE_GPS_OUTSIDE_PARCEL` (safe: statuses consumed
  loosely). **No `parcel_uuid` → skip (grandfather).**
- Extend `backend/tests/test_gps_corroboration.py`: inside ok; outside quarantine;
  buffer edge; env-gate off relaxes; **null parcel_uuid skips cleanly**.

### 1.5 — Portal registration UI (no Google key)
- `portal/src/pages/Projects.tsx` (EDIT) — a **Boundary** step: **Leaflet + OSM**;
  for the draw tool prefer **`@geoman-io/leaflet-geoman-free`** over `leaflet-draw`
  (leaflet-draw is effectively unmaintained — audit note), plus paste-GeoJSON /
  import-KML. On submit → POST → render approved / overlap-reason / area-mismatch
  inline. Self-contained, CSP-friendly.
- `portal/src/api.ts` (EDIT) — `createParcel`, `listParcels` + types.
- `portal/src/components/` — new `ParcelMap/` component (encapsulated Leaflet; keep
  map logic out of the page).

### 1.6 — App: reference the parcel (Drift v25→v26)
- `lib/data/local/app_database.dart` (EDIT) — bump to **v26**, add `MigrationStrategy`
  step; add `parcel_uuid` to batch record + outbox payload (optional field).
- `lib/ui/screens/lantana_sourcing_screen.dart` (EDIT) — replace the 0.3 placeholder
  with real read-only "Source parcel: <name>, approved".
- `test/migration_v25_to_v26_parcel_test.dart` (NEW) — v25 DB upgrades cleanly; old
  batches (null parcel) still read/sync.

**Tests summary (Part 1):** `test_geometry.py`, `test_parcels_endpoint.py` (NEW:
overlap reject/accept, invalid, area-mismatch, role gate), extended
`test_gps_corroboration.py`; portal `Projects.test.tsx` + `ParcelMap.test.tsx`
(draw→submit→reject reason); app migration + `parcel_uuid` carries.

**DoD.** Three suites green; geometry core has no I/O; overlap is anti-double-count
proven by test; old batches grandfather; env-gate toggles. Commit.

**Non-breaking:** `parcel_uuid` nullable everywhere; corroboration skips when absent;
new endpoint additive; app payload field optional (old app omits it → accepted).

---

## PART 2 — B: Farmer registry + KYC + FPIC consent + payments · P0 · L

> Depends on 0.2 (Project). Replaces the `// TODO: Save KYC` stub
> (`farmer_kyc_screen.dart:71`) which currently saves nothing.

### 2.1 — Data model + migrations (normalized, not one wide table)
- `backend/models.py` (EDIT) — `Farmer` + children `FarmerDocument`, `FarmerConsent`,
  `FarmerPayment` (per `PRODUCT_BLUEPRINT.md §B`). PII minimization: **store last-4
  only** for documents; mask account numbers. `mobile_number` unique per project.
- Migrations (NEW, chained): one per table, all additive.

### 2.2 — Endpoints (evidence pattern + role gate)
- `backend/routers/` → `farmers.py` (NEW) — device-side create via the evidence
  pattern (verify signature → ownership/enrollment → persist); `check-farmer-mobile`
  uniqueness. Portal read/search under `portal/routes.py` (`require_role`).
- `backend/schemas.py` / `portal/schemas.py` (EDIT) — explicit farmer + child schemas.
- Reuse `crypto_signer`/`security.py` to **hash + sign FPIC artifacts**.

### 2.3 — App onboarding flow (modular multi-step, one widget per step)
- `lib/ui/screens/farmer_kyc_screen.dart` (REPLACE stub) → decompose into a
  `lib/ui/screens/farmer_onboarding/` folder, **one file per step** (Personal,
  Identity, Address, Payment, Signature, FPIC, Review) + a coordinator notifier in
  `lib/providers/farmer_onboarding_notifier.dart`. No 500-line mega-widget.
- `lib/data/local/` — `farmer_writers.dart` (NEW) `insertFarmerWithOutbox` (+ children);
  Drift **v26→v27** adds farmer tables/payloads.
- `lib/services/sync_queue_manager.dart` (EDIT) — add `kEndpointByTable['farmers']`
  (+ children) and capture types. Reuse `SecureCaptureService` for all photos/PDF.
- FPIC: capture **signed PDF + photo of farmer holding it**, both SHA-256 + Ed25519.

### 2.4 — Portal
- `portal/src/pages/Farmers.tsx` (NEW) — list/search/detail (real fields only; missing
  = missing). `api.ts` + types.

**Tests:** `backend/tests/test_farmers.py` (create, uniqueness reject, consent
persisted, **last-4 only** enforced, role gate); app `test/farmer_onboarding_*_test.dart`
(each step's outbox payload correct; FPIC media hashed+signed) + Drift v26→v27
migration test; portal `Farmers.test.tsx`.

**DoD.** Three suites green; PII minimized + encrypted + signed; stub fully removed
(grep `Save KYC locally` → nothing). Commit.

**Non-breaking:** all new tables/routes additive; old app has no farmer flow → unaffected.

---

## PART 3 — C: Facility + Dispatch custody state machine + dual weighing · P0 · L

> Depends on 0.2. The biggest structural gap: biomass/biochar **moving between
> custodians**.

### 3.1 — Facility (precondition) + Dispatch model
- `backend/models.py` (EDIT) — `Facility` (`org_id` reserved for D),
  `Dispatch` + `DispatchSite` child (per `PRODUCT_BLUEPRINT.md §C`).
- Migrations (NEW, chained, additive).

### 3.2 — State machine (pure, test-first)
- `backend/services/dispatch_state.py` (NEW) — **pure** transition function
  `draft → in_transit → received`, rejects illegal transitions and **post-transit
  weight edits** (weight-lock). No DB inside; router calls it.
- `backend/tests/test_dispatch_state.py` (NEW, test-first) — legal/illegal transitions;
  weight-lock rejects edits after Submit; dual-weigh delta > tolerance flags.

### 3.3 — Endpoints + reconciliation
- `backend/routers/dispatch.py` (NEW) — create/transition (`_assert_ownership`),
  facility CRUD (`require_role`). Dual-weigh reconcile (source vs facility) → flag via
  the `corroboration.py` pattern (mirror `derive_plausibility_reasons`). Hash+sign both
  weigh tickets.

### 3.4 — App flows + receiving (modular)
- `lib/ui/screens/dispatch/` (NEW folder) — biomass dispatch, biochar dispatch,
  receiving; **consequence-explicit confirm** on Submit ("you cannot change weight
  details"). `insertDispatchWithOutbox`; Drift **v27→v28**; routes added to sync maps.

### 3.5 — Portal
- `portal/src/pages/Dispatch.tsx` (NEW) — tabbed All/In-Transit/Received; facility
  admin; mark-received.

**Tests:** `test_dispatch_state.py`, `test_dispatch_endpoint.py` (transitions,
weight-lock, dual-weigh flag, ownership); app dispatch screen payload + confirm gating
+ migration test; portal `Dispatch.test.tsx`.

**DoD.** Three suites green; state machine pure + fully covered; weights immutable
post-transit; signed dual-witnessed weights. Commit.

**Non-breaking:** additive; old app unaffected.

---

## PART 4 — Compete pack (P1; parallelizable once deps exist)

> Each is its own commit + DoD. Same §0 discipline. Ordered by leverage.

- **O — Video capture** · M. Extend `secure_capture_service.dart` +
  `secure_camera_screen.dart` with a video record mode (duration+size cap, **hash the
  final artifact, Ed25519-sign, sandboxed store — never DCIM**). New capture types
  `quenching_video`/`density_video` in `capture_types.dart` + sync maps. Wire into
  `pyrolysis_screen.dart` (quench) + F. Tests: records → sandboxed+hashed+signed;
  caps enforced; capture_type routes.
- **E — Capture-integrity gates** · M. Extend `secure_capture_service.dart`: on-device
  Laplacian blur gate, FOV stamp, framing overlay, geofence-to-parcel (reuse Part 1
  polygon/bbox on-device), live-GPS session. New signed media fields. Env-gate
  `DMRV_BLUR_GATE_ENFORCED`, `DMRV_GEOFENCE_CAPTURE`. Tests: blur blocks, geofence warns.
- **F — Bulk-density volume→mass** · M. `BulkDensityTest` model; wire optional
  volumetric mass path into `credit_engine`/`lca_engine` (pure math, tested);
  production gate `production_requires_valid_density`. Reuse BLE weight scale. Tests:
  volume×density mass; gate blocks without in-date density.
- **H — Media pipeline: compression/transcode + progress %** · M. Extend the outbox
  media phase; add compression pkg; **compress-before-hash** so the signed hash matches
  uploaded bytes; progress in `sync_health_screen.dart`. Keep two-phase commit. Tests:
  compress reduces size + hash matches; progress advances; resume after kill.
- **M — In-app capture review** · S. Confirm/retake in `secure_camera_screen.dart`;
  read-only thumbnail strip from **sandboxed** store (never DCIM) in
  `proof_wallet_screen.dart`. Tests: retake works; no DCIM export.
- **J — Field-UX pack** · M. Pincode/IFSC autofill, save-to-draft, consequence-explicit
  confirms, stage-labeled prompts, empty-states, en+hi strings. Each a small slice.
- **K — Per-media reviewer verdict loop** · S. `MediaFile.verification_status/remarks`
  + `PATCH media/{id}/verify` (`require_role("verifier","admin")`); portal verdict
  controls in `EvidenceGallery`/`EvidenceLightbox`; app surfaces "rejected: reason".
- **G — Config-driven methodology/registry** · M. `RegistryConfig` model; extract
  hardcoded CSI-3.2 constants into a **default config row** (regression: default ==
  current result); `credit_engine` selects config by facility; FPIC template keys off
  it. Do before more code hardens around one method.

**Part 4 DoD.** Each item: three suites green, env-gated, non-breaking, §0-clean,
one commit. After all: full regression green.

---

## PART 5 — Scale (post-launch; not required for production)

- **D** roles + multi-facility scoping → multi-tenancy (`VALID_ROLES` extend,
  `org_id`/`facility_id` scoping, tenant guard in `middleware.py`).
- **L** on-device ML: QR/barcode + document scanner (`mobile_scanner`, ML Kit).
- **N** observability breadth (Sentry perf/release-health) + iOS target.
- **A phase-2** Ed25519 signed field-walk link (reuses 0.1 key) → ground-truthed
  boundary. **PostGIS** migration when parcel volume makes the O(n) scan slow.

---

## §7. Production-Readiness Gate (the finish line)

Ship to production only when **all** are true:

**Feature completeness**
- [ ] Part 0 (0.1–0.4), Part 1 (A), Part 2 (B), Part 3 (C), Part 4 (O,E,F,H,M,J,K,G) done.
- [ ] No fabricated data anywhere (grep: no `polygon_captured`, `4 vertices`,
      `Save KYC locally`, no other "reports-uncaptured-data" stub).

**Integrity (moat) audit**
- [ ] Every new evidence artifact SHA-256 + Ed25519 signed; verified server-side.
- [ ] All new PII encrypted at rest (SQLCipher); no new plaintext/SharedPreferences PII.
- [ ] All new evidence flows through `insert*WithOutbox` + two-phase hash-verified sync.
- [ ] Server credit/LCA math unchanged in transparency; no client-trusted inputs.

**Non-breaking / migration audit**
- [ ] Every Alembic migration chains cleanly HEAD→…, `upgrade`+`downgrade` tested on a
      copy of prod-shaped data; backfills idempotent; zero orphans.
- [ ] Every Drift bump (v25→v26→v27→v28) has a migration test from the prior version;
      grandfathered old rows read/sync/corroborate.
- [ ] Old app + new backend = green (contract test). New app + old backend = graceful.
- [ ] No required field added to any signed JSON body (V4b-regression guard).

**Config / ops**
- [ ] All new gates env-flagged, default-on in code, documented in `PRODUCT_BLUEPRINT.md §6`.
- [ ] **Staged rollout proven:** each new quarantine gate was enabled on the live fleet
      via remote config (OFF → canary → observe → on), not flipped at deploy.
- [ ] Remote control plane live: kill-switch + min-version verified end-to-end.
- [ ] Server signing key provisioned + rotation (`kid`) proven; `docs/SERVER_SIGNING_KEY.md` written.
- [ ] Attestation decision recorded (stays OFF until Play Integrity creds — do not fake).

**Correctness / abuse-resistance (audit-added)**
- [ ] Invariant-enforcing writes (overlap, uniqueness, dispatch state) are DB-serialized;
      concurrent-writer tests pass.
- [ ] Every new evidence endpoint is idempotent (client UUID + upsert); duplicate-submit test passes.
- [ ] Compute-on-user-input endpoints (geometry) reject pathological input before the work.
- [ ] Every new gate/quarantine state emits a prometheus metric + structured log (verifiable in prod).

**Data protection (audit-added — B / any PII Part)**
- [ ] PII retention policy defined + enforced; data-subject erasure path (incl. synced
      copies) implemented + tested; PII-access audit log in the portal.
- [ ] DPDP-alignment note recorded; document types store last-4 only; accounts masked.

**UI parity (audit-added)**
- [ ] Every new app screen has en+hi strings (l10n test green).
- [ ] Every new portal page: zero jest-axe violations; growable lists cursor-paginated.
- [ ] Contract tests extended for every new/changed endpoint.

**Quality gates**
- [ ] Full backend `pytest` green; full flutter `flutter test` green; portal `vitest`
      + `tsc --noEmit` + `vite build` green.
- [ ] `/code-review` (or `/security-review`) run on the cumulative diff; findings
      resolved.
- [ ] No dead scaffolding, no debug prints, no TODO-without-ticket in shipped code.
- [ ] Release APK: signed + obfuscated + freerasp; installed + smoke-tested on the
      Micromax test device.

**Docs / handoff**
- [ ] Each Part has an updated runbook doc; this plan's checkboxes complete.
- [ ] New session-handoff written.

---

## §Verify — re-confirm before each Part (fresh session)

```bash
REPO="c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv"
git -C "$REPO" log --oneline -10
git -C "$REPO" status --short
# Alembic HEAD (expect d6e7f8a9bac1 until Part 0.2 adds the next):
cd "$REPO/backend" && python -m alembic heads
# Drift version (expect 25 until Part 1.6 bumps to 26):
grep "schemaVersion" "$REPO/lib/data/local/app_database.dart"
# Sync routing maps:
grep -n "kEndpointByTable\|kCaptureTypeByTable" "$REPO/lib/services/sync_queue_manager.dart"
```

Run the relevant suites before starting and after finishing every Part:
```bash
cd "$REPO/backend" && python -m pytest -q                 # ~4.5 min
cd "$REPO" && /c/Users/bit/development/flutter/bin/flutter test   # ~4 min
cd "$REPO/portal" && npx vitest run && npx tsc --noEmit && npx vite build
```
(Run long suites in the background per the dev-box constraints; toggle Windows
Developer Mode before flutter builds.)

---

## Appendix — migration chaining ledger (fill in as you go)

| Part | Alembic revision (new) | down_revision | Drift bump |
|------|------------------------|---------------|------------|
| 0.2  | _(alembic revision -m create_project_table_and_backfill)_ | `d6e7f8a9bac1` | — |
| 0.4  | app_config | (0.2) | — |
| 1.2  | source_parcel + batch.parcel_uuid | (0.4) | v25→v26 |
| 2.1  | farmer + children | (1.2) | v26→v27 |
| 3.1  | facility + dispatch + dispatch_site | (2.1) | v27→v28 |
| 4.F  | bulk_density_test | (3.1) | v28→… |
| 4.K  | media verification cols | … | — |
| 4.G  | registry_config | … | — |

> Never hand-author revision hashes — let `alembic revision` generate them and set
> `down_revision` to the current HEAD. Record the generated id here for traceability.
