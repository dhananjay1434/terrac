# TerraCipher dMRV — Product Build Blueprint (Varaha-gap closure, architecture-exact)

**Purpose.** A PM/architect blueprint for every capability we lack versus Varaha
"Kalki", mapped to *exact* insertion points in our stack — which model, which
Alembic migration, which sync route, which Flutter screen/writer, which portal
page, which corroboration hook, which tests. Build from this without re-deriving.

**Read order.** §1 principles → §2 architecture map (the reusable rails) → §3
gap inventory → §4 per-feature blueprints (A–N) → §5 sequenced roadmap → §6
cross-cutting. Each blueprint uses the same template: *Why · Where · Data model ·
Screens/UX · Integrity hooks · Build steps · Tests · Effort/Priority · Reuse &
moat.*

Effort: **S** ≤1 sprint · **M** 1–2 · **L** 3+. Priority: **P0** blocker /
credibility · **P1** compete · **P2** differentiator/scale.

---

## 1. Guiding principles (non-negotiable)

1. **Protect the moat in every feature.** Encryption-at-rest (SQLCipher),
   per-submission Ed25519 signing + replay window, sensor-grounded measurement
   (BLE temp/weight + ATECC608B attestation), transparent server credit engine,
   verifier portal. Every new capability must preserve signed-canonical +
   encrypted guarantees. If a feature would weaken them, redesign it.
2. **Reuse the rails, don't reinvent.** New evidence → `insertWithOutbox` +
   `SyncOutbox` + a `kEndpointByTable` route + a backend evidence endpoint
   guarded by `_assert_batch_ownership`. New portal action → `require_role`. New
   capture → `SecureCaptureService` (already GPS/EXIF/SHA/orientation/mock).
3. **Every new compliance/anti-fraud gate is ENV-GATED** (default on), mirroring
   `COMPLIANCE_ENFORCED`, `DMRV_REQUIRE_EXIF_GPS`, `TRANSPORT_EVENTS_ENFORCED` —
   so demos/edge deployments relax without a code change.
4. **Test-gate every phase.** Backend `pytest`, app `flutter test`, portal
   `vitest`+`typecheck`+`build`. One phase per commit.
5. **Be more defensible than Varaha, not just equal.** Where they have a feature,
   we add it *plus* the signing/encryption/sensor layer they can't retrofit.
6. **Never fabricate.** No stub that claims captured data it didn't capture (kill
   the boundary boolean). Missing data shows as missing.

---

## 2. Architecture map — the rails every blueprint plugs into

**Backend (FastAPI + SQLAlchemy async + Postgres/Render):**
- Models: `backend/models.py` (`Batch`, `Kiln`, `EndUseApplication`,
  `MoistureReading`, `CompositePileSample`, `TransportEvent`, `AnnualVerification`,
  `MediaFile`, `PortalUser`, `EnrollmentToken`). `Batch` has `latitude/longitude`,
  `project_id`, `status`.
- Migrations: `backend/alembic/versions/` (create tables, add columns).
- Evidence endpoints: `backend/routers/evidence.py` (pattern: verify device
  signature → `_assert_batch_ownership` → persist → recompute). Portal endpoints:
  `backend/portal/routes.py` (pattern: `require_role(...)`).
- Compliance/credit: `corroboration.py` (`derive_*` gate functions),
  `credit_engine.py` (`recompute_batch_credit`), `lca_engine.py` (CSI 8-step),
  `geo.py` (GPS corroboration + quarantine).
- Auth/security: `security.py` (Ed25519 verify + skew), `portal/auth.py`
  (argon2id, `require_role`, `VALID_ROLES=(admin,lab,verifier)`), `middleware.py`
  (rate-limit + body cap), `attestation.py`, `settings.py` (fail-loud env).
- Status vocab: `batch.status` values are consumed loosely (only `ISSUED` is
  special-cased) → new `QUARANTINE_*`/state strings are safe to add.

**App (Flutter + Drift/SQLCipher):**
- DB: `lib/data/local/app_database.dart` (schema v25, `insertWithOutbox`,
  per-domain `insert*WithOutbox` writers), `tables.dart`.
- Sync: `lib/services/sync_queue_manager.dart` (`SyncOutbox` two-phase via
  `json_synced_at`/`media_synced_at`, `kEndpointByTable`, `kCaptureTypeByTable`,
  atomic CAS row-claim, backoff, `retryNow`).
- Crypto: `lib/services/crypto_signer.dart` (Ed25519, `signRequestV2`,
  `signMediaUpload`). Capture: `secure_capture_service.dart` (GPS/EXIF/SHA-256/
  azimuth/pitch/roll/isMocked, sandboxed). Sensors: `ble_temperature_service.dart`,
  `ble_weight_scale_service.dart`. RASP: `device_integrity_service.dart`.
- Vocab: `lib/data/capture_types.dart` (`CaptureType` constants).
- Screens: `lib/ui/screens/` (enrollment, lantana_sourcing, moisture_verification,
  kiln_select, pyrolysis, yield_scale, composite_sample, end_use_application,
  sync_health, proof_wallet, dashboard, farmer_kyc). i18n: `lib/l10n/app_en.arb`,
  `app_hi.arb`.

**Portal (React/TS + vitest):**
- `portal/src/api.ts`, `auth.ts` (token, `getRole`), `pages/` (Registry,
  Batches, BatchDetail, Login), `components/` (EvidenceGallery, EvidenceLightbox,
  ComplianceChecklist, ConfirmModal, DataTable).

---

## 3. Gap inventory (ranked; drives §5 sequence)

| ID | Feature | Priority | Effort | Class |
|----|---------|----------|--------|-------|
| 0 | **Project entity** (prerequisite — A/B/C/D/G scope off it; today `project_id` is a bare string, no table) | P0 | S | prerequisite |
| A | Source-parcel boundary + overlap + point-in-polygon corroboration | P0 | L | table-stakes→differentiator |
| B | Farmer registry + KYC + hash-anchored FPIC consent + payments | P0 | L | table-stakes→differentiator |
| C | Facility entity + Dispatch custody state machine + dual weighing | P0 | L | table-stakes |
| D | Field roles + multi-facility scoping (+ later multi-tenancy) | P1 | L | table-stakes |
| E | Capture-integrity gates (blur, FOV, framing overlay, geofence, live GPS) | P1 | M | differentiator |
| F | Bulk-density volume→mass activity, production-gated | P1 | M | table-stakes |
| G | Config-driven methodology/registry (`registry_config_id`) | P1 | M | table-stakes→platform |
| H | Media pipeline: compression/transcode + upload progress % | P1 | M | table-stakes |
| I | Remote control plane: feature flags + kill-switch + min-version | P0 | M | table-stakes (ops safety) |
| J | Field-UX pack (pincode/IFSC autofill, drafts, confirms, prompts, empty-states) | P1 | M | table-stakes |
| K | Per-media reviewer verdict loop (portal) | P1 | S | differentiator |
| L | On-device ML: QR/barcode scanner + document scanner | P2 | M | differentiator |
| M | In-app capture review (thumbnails/retake) | P1 | S | table-stakes (field UX) |
| N | Observability breadth + iOS | P2 | M/L | scale |
| O | In-app **video capture** (quenching/mulching/density) — SecureCapture is photo-only today | P1 | M | table-stakes (methodology-required) |

**Consciously deferred (noted, not forgotten):** per-day facility rollup
(Varaha `artisanal_summary`, analytics only — revisit with D/facility); Varaha's
saved-number / phone-OTP login is **N/A by design** — our auth is device-Ed25519
enrollment, not phone OTP, so we intentionally do not build it.

---

## 4. FEATURE BLUEPRINTS

### 0 — Project entity (PREREQUISITE) · P0 · S

**Why.** Audit finding: **there is no `Project` table.** `project_id` is a bare
`String(128)` column on `Batch` (`models.py:333`) and `AnnualVerification`
(`models.py:266`). But A (parcel scoping/overlap), B (farmer→project), C
(facility→project), D (org/tenancy), and G (registry binding) all treat "project"
as a real entity. Build this **first**, or every one of those hangs off an
un-scoped string with no metadata, no registry binding, no tenancy anchor.

**Where.** Backend: new `Project` model in `models.py` + Alembic migration; a
FK/soft-link from `Batch.project_id`, `AnnualVerification.project_id`,
`SourceParcel.project_id` (A), `Farmer.project_id` (B), `Facility.project_id`
(C). Portal: a minimal Projects admin (create/list) under `Registry.tsx` or a
new page (`require_role("admin")`).

**Data model (`project`).** `project_uuid PK (or keep string project_id as the
natural key for back-compat), name, registry_config_id (→ G, nullable),
org_id (→ D, nullable), status('active'|'closed'), created_at`. Keep the existing
string `project_id` as the join key so **existing batches don't break**
(back-compat: the string becomes an FK-by-value into `project.project_id`).

**Integrity/back-compat.** Existing rows carry `project_id` strings today →
seed a `project` row per distinct existing `project_id` in the migration so
nothing orphans. New scoping (overlap in A, tenancy in D) keys off this table.

**Build steps.** 1) `Project` model + migration + backfill from distinct
existing `project_id`s. 2) Point A/B/C's new tables at it. 3) Portal Projects
admin. 4) (with G) attach `registry_config_id`; (with D) attach `org_id`.

**Tests.** Backend: project create; batch/parcel/farmer resolve their project;
backfill covers existing `project_id`s (no orphans). Portal: create/list.

**Reuse & moat.** `require_role`, Alembic pattern. Unblocks A/B/C/D/G cleanly.

---

### A — Source-parcel boundary + overlap + corroboration  · P0 · L

**Why.** The boundary = biomass **source parcel**. It proves feedstock
provenance, ties to a consenting owner (FPIC), and — via overlap rejection —
prevents two projects claiming the same land (**double-counting, the highest-value
carbon fraud**). Today we ship a *fake stub* that persists a boolean; killing it
is also a credibility fix. (Full geometry math + Phase-2 field-walk mechanics
already specced in `docs/BOUNDARY_DESIGN.md` — this section is the build plan.)

**Where.**
- Backend model: new `SourceParcel` in `models.py`; add nullable
  `Batch.parcel_uuid`. Migration in `alembic/versions/`.
- Geometry libs: add `shapely` + `pyproj` to `requirements.txt` (no PostGIS for
  MVP; bbox prefilter to avoid O(n²); PostGIS later at scale).
- Endpoint: `POST /api/v1/portal/parcels` (`require_role("admin")`) — validate +
  overlap-check + store. `GET /parcels?project_id=`.
- Corroboration: extend `geo.py::_evaluate_anchor` — if batch has `parcel_uuid`,
  check EXIF GPS `point-in-polygon(buffer≈25m)`; outside → new status
  `QUARANTINE_GPS_OUTSIDE_PARCEL`.
- Portal: new **Boundary** step in project/site setup (extend `Registry.tsx` or
  a new `Projects` page) using **Leaflet + OSM + leaflet-draw** (no Google key),
  plus paste-GeoJSON / import-KML.
- App: **remove** `captureGpsPolygon()` boolean in
  `lantana_sourcing_notifier.dart`; batch references `parcel_uuid` (read-only
  "Source parcel: <name>" on the sourcing screen).

**Data model (`source_parcel`).** `parcel_uuid PK, project_id FK, name,
boundary_geojson TEXT, area_m2, declared_area_acres, bbox_min_lat/lon,
bbox_max_lat/lon, boundary_method('portal_drawn'|'field_walk'|'imported'),
boundary_status('approved'|'pending_review'|'rejected'), created_by_user_id,
created_at`. `Batch.parcel_uuid` nullable (grandfather).

**Integrity hooks.** Overlap gate `DMRV_PARCEL_OVERLAP_ENFORCED` (default on):
`shapely` validity (`make_valid`/reject), geodesic area via
`pyproj.Geod.geometry_area_perimeter`, overlap in projected meters with an
**absolute sliver floor (~200 m²) + ratio (~2%)** so adjacent parcels aren't
falsely rejected. Area-mismatch flag at ±15%.

**Build steps.** 1) Backend model+migration+`shapely`/`pyproj`+overlap endpoint
(the anti-double-count core). 2) geo.py point-in-polygon corroboration. 3) Portal
Leaflet draw/import + registration UI. 4) App: kill fake stub, add `parcel_uuid`
ref (Drift v25→v26 adds it to batch/outbox payload). 5) (P2) Ed25519 signed
field-walk link (see `BOUNDARY_DESIGN.md` §6).

**Tests.** Backend: overlap accept/reject, invalid polygon, area-mismatch,
point-in-polygon inside/outside/buffer edge, env-gate off (extend
`test_gps_corroboration.py`). App: batch carries `parcel_uuid`; regression that
`captureGpsPolygon` no longer persists a boolean. Portal: draw→submit→reject
reason renders; role gate.

**Reuse & moat.** Reuses `require_role`, `geo.py`, our signed/hashed GPS. Moat:
every photo's **Ed25519-signed** GPS proven inside an approved, non-overlapping
parcel — "signed evidence inside sanctioned land," not just "a boundary exists."

---

### B — Farmer registry + KYC + FPIC consent + payments · P0 · L

**Why.** Legal/credit-eligibility blocker: registries require documented **FPIC
consent**; a real program needs a persisted **farmer** identity + **payout**
details. Today: a `// TODO` stub (`farmer_kyc_screen.dart`) that saves nothing.

**Where.**
- Backend: `Farmer` model (+ `FarmerDocument`, `FarmerConsent`, `FarmerPayment`)
  in `models.py`; migrations. Endpoints under `backend/portal/routes.py` +
  device-side create via evidence pattern; `check-farmer-mobile` uniqueness.
- App: replace the stub with a real multi-step onboarding flow; new
  `insertFarmerWithOutbox` + `kEndpointByTable['farmers']='farmers'`.
- Portal: farmer list/search/detail under a new `Farmers` page.

**Data model.** `farmer(farmer_uuid PK, project_id, first_name, last_name,
gender, guardian_name, dob, mobile_number UNIQUE-per-project, education,
family_size, reported_area, village/address block, kyc_status, consent_status,
signature_media_id, created_at, sync_status)`. `farmer_document(doc_type
[aadhaar|pan|passport|nid], last4, media_id-hashed)`. `farmer_payment(rail
[bank|upi|mfs], account_holder, masked_account, ifsc/branch, upi_id, mfs_id)`.
`farmer_consent(fpic_template_id, signed_pdf_media_id, holding_photo_media_id,
signed_at, exclusivity_ack bool)`.

**Screens (app, multi-step, Voyager-equivalent via our nav).**
1. **Personal** — name/gender/guardian/DOB/village/area/family/crop + profile
   photo (SecureCapture).
2. **Identity** — doc type (country-aware) + photo (SecureCapture, SHA-anchored),
   store **last-4 only** in the row.
3. **Address** — village/block/district; (P2) pincode auto-fill (see J).
4. **Payment** — UPI or bank (IFSC lookup P2); mask account number at rest.
5. **Signature** — finger-draw canvas → media.
6. **FPIC** — display template → operator reads → farmer signs → **capture signed
   PDF + photo of farmer holding it, both SHA-256 + Ed25519 anchored**.
7. **Review/Submit** — writes farmer + children via outbox.

**Integrity hooks.** Mobile-number uniqueness (server + local). **Hash-anchor +
sign the FPIC artifacts** (SecureCapture already hashes; sign via
`crypto_signer`) — we can *prove* consent, which Varaha (unsigned, plaintext)
cannot. Encrypt PII at rest (already SQLCipher) — a marketable lead.

**Build steps.** 1) Backend farmer + children models/migrations/endpoints +
uniqueness. 2) App onboarding flow + writers (reuse SecureCapture + outbox). 3)
FPIC template fetch + signed-consent capture. 4) Portal farmer list/detail. 5)
Payments (UPI first, bank/IFSC later).

**Tests.** Backend: farmer create, uniqueness reject, consent persistence, last-4
only. App: each step persists correct outbox payload; FPIC media hashed+signed.
Portal: list/search/detail render real fields.

**Reuse & moat.** Reuses SecureCapture, outbox, Ed25519, SQLCipher. Moat:
**hash-anchored, signed, encrypted consent + KYC** vs Varaha's plaintext unsigned.

---

### C — Facility entity + Dispatch custody state machine + dual weighing · P0 · L

**Why.** The defining primitive of a supply chain: represent biomass/biochar
**moving between locations under different custodians**. Today we can't. Enables
receiving, reconciliation, and multi-crew ops.

**Where.**
- Backend: `Facility` model (+ `organization_id` reserved for D); `Dispatch` +
  `DispatchSite` (child); migrations. Endpoints: dispatch create/transition
  (`_assert_ownership`), facility CRUD (`require_role`).
- App: dispatch capture flow + receiving screen; `insertDispatchWithOutbox`;
  routes `dispatch`/`facility`.
- Portal: facility admin + dispatch list (tabbed All/In-Transit/Received).

**Data model.** `facility(facility_uuid PK, org_id, name, type
[artisanal|industrial], state, district, location_wkt, registry,
registry_config_id [see G], status)`. `dispatch(dispatch_uuid PK, kind
[biomass|biochar], source_ref, dest_facility_uuid/dest_farmer_uuid, status
[draft|in_transit|received], weight_source, weight_source_method,
weight_source_pdf_media, weight_facility, weight_facility_pdf_media, empty_truck,
loaded_truck, driver_name, driver_phone, truck_number, truck_image_media,
invoice_media, created_at, sync_status)`. `dispatch_site(dispatch_uuid FK,
parcel_uuid/site_id, moisture, moisture_image_media, truck_percentage_filled,
truck_load_image_media)`.

**Screens (app).** Biomass dispatch: moisture(+photo) → weight(method, tare,
truck-fill %) → truck-load (multi-site aggregate) → driver → **overview → Submit
(→ In-Transit, weights LOCK)** with a **consequence-explicit confirm** ("you
cannot change weight details"). Biochar dispatch: farm select → weight →
driver → truck(+image) → invoice → Submit. Facility receiving:
shipments list → detail → **re-weigh** → **"Mark as Received"** (+ receive
photo).

**Integrity hooks.** **Weight-lock on transition** (immutable after Submit);
**sequential-stage gating**; **dual weighing** → reconcile source vs facility,
delta > tolerance → corroboration flag (mirror `derive_plausibility_reasons`);
hash+sign both weigh tickets (beats Varaha's unsigned slips).

**Build steps.** 1) `Facility` model + admin (portal + app select) — precondition.
2) `Dispatch` + `DispatchSite` + state machine + endpoints. 3) App capture flows
+ receiving. 4) Dual-weigh reconciliation flag. 5) Portal dispatch list.

**Tests.** Backend: state transitions (draft→transit→received), weight-lock
rejects post-transit edits, dual-weigh delta flag, ownership. App: each screen's
outbox payload; confirm-dialog gating. Portal: tabbed list, mark-received.

**Reuse & moat.** Outbox, `_assert_ownership`, SecureCapture. Moat: signed,
hash-anchored, dual-witnessed weights.

---

### D — Field roles + multi-facility scoping (+ later multi-tenancy) · P1 · L

**Why.** Single-device ownership doesn't scale past a pilot. Multi-crew operators
need roles (Site/Facility Manager, Enumerator) + facility scoping; multi-org
tenancy to run >1 customer on one backend.

**Where.** Extend `portal/auth.py VALID_ROLES` with field roles; add
`organization_id`/`facility_id` scoping columns to facility-bound entities; a
tenant guard in `middleware.py`. App: role/facility selector post-enrollment.

**Data model.** `organization(org_uuid, name, status[pending|approved|active])`;
`user_facility(user_id, facility_uuid, role)`; add `org_id` to facility/dispatch/
farmer. Reserve a tenant header (name TBD — we verified Varaha's isn't public;
choose our own, documented).

**Build steps.** 1) Roles + facility scoping (single-org). 2) Facility selector +
role switch in app. 3) (P2) org/tenant isolation + approval lifecycle.

**Tests.** Role-gated endpoints reject wrong role; facility-scoped queries;
org-isolation.

**Reuse & moat.** `require_role`, argon2 portal auth. Keep Ed25519 device model.

---

### E — Capture-integrity gates (blur, FOV, framing, geofence, live GPS) · P1 · M

**Why.** Machine-verifiable evidence quality. Varaha rejects blurry photos at
capture, records FOV/tilt, geofences capture to the parcel, and tracks GPS for
the whole session. We capture orientation+GPS+mock but not FOV/blur/geofence.

**Where.** Extend `secure_capture_service.dart` + `secure_camera_screen.dart`;
backend accepts new fields on `MediaFile`.

**What to add.**
- **Blur/sharpness gate** — on-device Laplacian-variance score; below threshold →
  block/retake. (No server ML.)
- **Camera FOV** — read from `CameraController` and stamp into media metadata.
- **Framing overlay** — extend the existing crosshair to a fit-to-box/dashed-oval
  for standardized shots; require **asset ID (kiln) visible** via stage copy.
- **Geofenced capture** — if the batch has a `parcel_uuid`, warn/block when the
  live fix is outside the parcel (reuse A's polygon on-device or a cached bbox);
  "move closer, Xm outside."
- **Live GPS session** — track for the capture duration; stamp accuracy; flag
  jumps. Emit start/update events (feeds observability, N).

**Data model.** Add to media metadata: `fov_h/v/diag`, `blur_score`,
`gps_accuracy`, `geofence_ok`.

**Integrity hooks.** All new fields ride the existing signed media hash → still
tamper-evident. Env-gate `DMRV_BLUR_GATE_ENFORCED`, `DMRV_GEOFENCE_CAPTURE`.

**Tests.** App: blur below threshold blocks; FOV stamped; geofence outside →
warn. Backend: media accepts + stores new fields.

**Reuse & moat.** SecureCapture pipeline. Moat: signed FOV/blur/geofence — Varaha
has the metadata unsigned.

---

### F — Bulk-density as volume→mass activity, production-gated · P1 · M

**Why.** Artisanal biochar can't go on a truck scale mid-process; mass =
`kiln_volume × density`. Varaha gates production on an in-date, evidenced density
calibration. We store a density field but never use it for mass.

**Where.** Backend: `BulkDensityTest` model + wire into `credit_engine`/
`lca_engine` mass path (optional volumetric route when no direct weight). App:
density capture screen (reuse **BLE weight scale** for mass + a short video/photo)
+ writer. Gate the burn/yield step on a valid density (mirror
`scale_calibration_expired`).

**Data model.** `bulk_density_test(test_uuid, facility_uuid, density,
performed_at, mass_kg, volume_l, mass_image_media, video_media, valid_until)`.

**Integrity hooks.** Production hard-gate `production_requires_valid_density`
(env-gated). Density-derived mass flagged as such in the LCA audit.

**Tests.** Backend: volume×density mass path; gate blocks without in-date density.
App: capture writes density + evidence.

**Reuse & moat.** BLE scale service, outbox, calibration-gate pattern.

---

### G — Config-driven methodology / registry · P1 · M

**Why.** `lca_engine` hardcodes `CSI-3.2`. To serve >1 program/registry (biochar/
ARR/regen, Puro/Verra), methodology + consent templates must be **config, not
code** — the demo→platform line. Do before more code hardens around one method.

**Where.** Backend: `RegistryConfig` model (methodology params, factors, FPIC
template set) referenced by `facility.registry_config_id`; `credit_engine`
selects the config per batch's facility. Keep `lca_engine` pure; pass params in.

**Data model.** `registry_config(config_id, registry_name, methodology_version,
params_json, fpic_template_set_id)`.

**Build steps.** 1) Extract hardcoded CSI constants into a default config row. 2)
`credit_engine` reads config by facility. 3) FPIC template selection keys off it.

**Tests.** Two configs → two credit results from same inputs; default config ==
current behavior (regression).

**Reuse & moat.** Keeps the transparent signed engine; adds flexibility.

---

### H — Media pipeline: compression/transcode + upload progress · P1 · M

**Why.** Full-res uploads stall on rural bandwidth with no feedback → farmer
data-loss/trust risk. Varaha compresses/transcodes + shows 0–100%.

**Where.** Extend `sync_queue_manager.dart` media phase + a preprocess step;
add an image/video compression package to `pubspec.yaml`; surface progress in
`sync_health_screen.dart` + dashboard.

**What to add.** Image compress (target <500 kB already for capture; add for
imported), video transcode, a conversion-status column, upload **progress %** per
media, and keep our **two-phase hash-verified commit** (assert `server_sha256`
before delete). Optionally presigned-upload later.

**Integrity hooks.** Hash the **final** artifact (compress before hash, as
capture already does) so the signed hash matches the uploaded bytes.

**Tests.** App: compression reduces size + hash matches post-compress; progress
advances; resume after kill.

**Reuse & moat.** Two-phase commit stays; add convenience without losing the
hash guarantee.

---

### I — Remote control plane: flags + kill-switch + min-version · P0 · M

**Why.** Private-APK + CI-off = **zero remote control of a deployed fleet**. A
bad build or discovered fraud vector can't be flag-gated or force-updated. Ops
safety P0. (Doesn't need Firebase — a **signed boot-time config** suffices.)

**Where.** Backend: `GET /api/v1/config` returning an **Ed25519-signed** JSON
(feature flags, min-supported-version, kill-switch, message). App: fetch at boot,
verify offline with the server public key (same key as A's field-walk link),
cache; enforce min-version (block + "update required"), honor kill-switch.

**Data model.** Server config doc (flags map, `min_version`, `kill_switch`,
`message`, `signed_at`, signature).

**Build steps.** 1) Signed config endpoint. 2) App boot fetch + verify + cache +
enforce. 3) Portal admin to edit flags. 4) Min-version gate ties to in-app-update
(self-hosted APK version check).

**Tests.** Backend: config is signed. App: tampered config rejected; below
min-version blocks; kill-switch disables.

**Reuse & moat.** Ed25519 (server-signs, app-verifies — same direction as A).
This is also the "respond to a live incident" capability.

---

### J — Field-UX pack · P1 · M

**Why.** Small ergonomics that cut field error/time for rural agents.

**Where/what (each small, ship incrementally).**
- **Pincode → address auto-fill** (India `api.postalpincode.in`) + review step —
  in address screens (B/farmer, facility).
- **IFSC → bank lookup** (`ifsc.razorpay.com`) — in payment screen (B).
- **Save-to-Draft** everywhere — add a `draft` flag to outbox/domain rows +
  a Drafts list; resume in-progress captures.
- **Consequence-explicit confirm dialogs** — replace generic guards with copy
  naming the exact loss ("finalizing locks the weight/temperature readings").
- **Stage-labeled photo prompts** — per-stage copy in pyrolysis capture ("~90%
  of run, pre-quench, kiln ID visible").
- **Actionable empty-state guidance** on every list (extend the few we have).
- **Day-start audit lock** (optional, when facilities exist) — gate the day's
  logging behind a fresh facility proof.
- i18n: add strings to `app_en.arb`/`app_hi.arb`.

**Tests.** App: pincode fills fields; draft persists+resumes; confirm copy shown.

**Reuse & moat.** Pure Flutter + our i18n (we already have en/hi — ahead of
Varaha's English-only).

---

### K — Per-media reviewer verdict loop (portal) · P1 · S

**Why.** Let a verifier bounce ONE photo with a reason (targeted recapture) vs
all-or-nothing. Varaha has `verification_status`/`remarks` per media.

**Where.** Backend: add `verification_status`/`verification_remarks` to
`MediaFile` + a `PATCH media/{id}/verify` (`require_role("verifier","admin")`).
Portal: verdict controls in `EvidenceGallery`/`EvidenceLightbox`. App: surface
"rejected: <reason>" on the batch → drives recapture.

**Tests.** Backend: verdict persists, role-gated. Portal: reject with remark
renders.

**Reuse & moat.** Our verifier portal already exists — this deepens it (Varaha
has no verifier product).

---

### L — On-device ML: QR/barcode + document scanner · P2 · M

**Why.** We *generate* a batch QR but can't *scan* it; scanning binds kiln +
composite bag + lab sample by scan (kills manual-entry error). Doc scanner
(edge/perspective) improves ID/land-doc capture (pairs with B).

**Where.** Add a scanner package (`mobile_scanner`); a scan action in
`kiln_select_screen`, composite/lab flows; ML Kit doc scanner in B's identity
step. Reuse the V6 `parseEnrollmentQr`-style parsers.

**Tests.** App: scan resolves kiln/batch code; doc scan returns a hashed image.

**Reuse & moat.** Our QR value format + SecureCapture hashing.

---

### M — In-app capture review (thumbnails / retake) · P1 · S

**Why.** Field agents can't currently re-view most captures (Proof Wallet shows
hashes, not images) → can't confirm a shot is usable. Add a **read-only
thumbnail strip per batch + capture confirm/retake** — WITHOUT breaking the
write-once/hashed/sandboxed model (render from our sandboxed store, never the OS
gallery).

**Where.** `secure_camera_screen.dart` (add confirm/retake after shoot);
`proof_wallet_screen.dart` or a new per-batch media view (thumbnails from
sandboxed files); keep hashes visible.

**Tests.** App: capture shows confirm/retake; thumbnail strip renders sandboxed
images; no export to DCIM.

**Reuse & moat.** Keeps hash-as-proof + sandbox; adds usability.

---

### N — Observability breadth + iOS · P2 · M/L

**Why.** Sentry-only lacks perf/adoption/crash-free-session insight; iOS scaffold
unshipped.
**Where.** Extend Sentry (perf traces, release health) before a second SDK; wire
the capture GPS-session events (E) as analytics. iOS: finish the Flutter iOS
target when a customer needs it (cheaper than Varaha's KMP).

---

### O — In-app video capture · P1 · M

**Why.** Audit finding: **`SecureCaptureService`/`secure_camera_screen` are
photo-only** (no video/record code). But quenching video is a **methodology-
required** artifact (a still can't prove a quench) and Varaha mandates it for
quenching/mulching/bulk-density. This is an omitted feature, not a detail.

**Where.** Extend `lib/services/secure_capture_service.dart` +
`secure_camera_screen.dart` to record video (CameraX video via the camera
plugin); wire into the pyrolysis quenching stage (`pyrolysis_screen.dart`),
bulk-density (F), and mulching (if C/sourcing adds it). Reuse the outbox media
path; transcoding handled by H.

**Data model.** No new table — video is a `media` artifact with a
`capture_type` (e.g. `quenching_video`, `density_video`) via `capture_types.dart`
+ `kCaptureTypeByTable`, same as photos.

**Integrity hooks.** Same pipeline as photos: sandboxed store (never DCIM),
**SHA-256 + Ed25519-sign** the final file, EXIF/GPS + timestamp, mock-location
flag. Because it rides the existing signed-media rail, a video is as
tamper-evident as our photos — and **signed**, unlike Varaha's.

**Build steps.** 1) Add video record mode to SecureCapture (duration cap, size
cap, hash the final artifact). 2) Add `quenching_video`/`density_video` capture
types + routes. 3) Wire into quenching + bulk-density stages. 4) Transcode +
progress via H.

**Tests.** App: video records → sandboxed + hashed + signed; capture_type routes
correctly; size/duration caps enforced.

**Reuse & moat.** SecureCapture + outbox + H transcode. Moat: signed video
evidence.

---

## 5. Sequenced roadmap (realistic critical path — NOT all-parallel)

Audit note: the prior draft stacked three large P0s in one phase — unrealistic.
This is a dependency-ordered critical path. Do the small unblockers first; run at
most **one large (L) workstream at a time** unless you have parallel teams.

**Step 0 — Now, this week (small, credibility + unblock):**
- **Kill the boundary fake stub** (A step 4, S) — stop shipping a false
  attestation. Do immediately, independent of everything else.
- **Build the Project entity** (Blueprint 0, S) — the prerequisite that unblocks
  A/B/C/D/G. Small, must precede them.
- **Remote control plane** (I, M) — ops safety; independent, high value, needed
  before any wider field deployment (kill-switch + min-version).

**Step 1 — the credibility core (one L at a time):**
- **A** Source-parcel boundary + overlap + point-in-polygon corroboration
  (backend core → geo.py → portal Leaflet → app parcel reference). The
  anti-double-count + provenance win; depends on Project entity.

**Step 2 — the legal/eligibility core:**
- **B** Farmer registry + KYC + **hash-anchored FPIC consent** + payments.
  Depends on Project entity; unblocks a real farmer program.

**Step 3 — the supply-chain primitive:**
- **C** Facility entity + Dispatch custody state machine + dual weighing.
  Depends on Project entity; the biggest structural product gap.

**Step 4 — compete pack (P1, parallelizable, mostly M/S):**
- **O** video capture · **E** capture-integrity gates · **F** bulk-density ·
  **H** media pipeline · **M** in-app review · **J** field-UX pack ·
  **K** reviewer loop · **G** registry-config.

**Step 5 — scale (P2):**
- **D** roles/multi-facility → multi-tenancy · **L** ML scanners ·
  **N** observability/iOS · **A** Phase-2 signed field-walk link ·
  PostGIS when parcel volume demands a spatial index.

**Throughout:** lead every pitch with the moat (signed + encrypted + sensor +
verifier); ship the security scorecard vs Varaha.

---

## 6. Cross-cutting

- **Env flags** (all default-on, relax for demo): `DMRV_PARCEL_OVERLAP_ENFORCED`,
  `DMRV_GEOFENCE_CAPTURE`, `DMRV_BLUR_GATE_ENFORCED`,
  `production_requires_valid_density`, plus existing `DMRV_REQUIRE_EXIF_GPS`,
  `COMPLIANCE_ENFORCED`, `TRANSPORT_EVENTS_ENFORCED`, `DMRV_ATTESTATION_ENFORCED`.
- **Migrations:** Alembic per new table/column; Drift v25→v26+ for
  `parcel_uuid`, farmer/dispatch payloads, draft flags, media metadata.
- **Status vocab:** new `QUARANTINE_GPS_OUTSIDE_PARCEL`, dispatch states — safe
  (loosely consumed).
- **Server signing key:** A (field-walk link) + I (config) both need a server
  Ed25519 keypair (server-signs/app-verifies) with a `kid` rotation scheme —
  build it once, both reuse it.
- **Don't copy Varaha's mistakes:** plaintext PII, unsigned evidence, shipped
  network inspector, secrets in the bundle. Every feature here keeps our
  encrypted + signed guarantees.
