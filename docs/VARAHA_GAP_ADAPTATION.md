# What to Adapt from Varaha "Kalki" — dMRV Gap & Adaptation Plan

> Gap analysis of the Kon-Tiki dMRV (this repo) against the reverse-engineered Varaha Biochar
> "Kalki" app. Only features that **genuinely belong in a dMRV** are listed — Varaha-specific
> operational cruft is excluded. Each item: *what Varaha has · why a dMRV needs it · what we have
> today · how to adapt (keeping our security model) · where it plugs in.*

**Guiding rule:** adopt the *feature*, not Varaha's *implementation*. Every new artifact (consent,
boundary, applicant) must be Ed25519-signed + SHA-256-hashed + SQLCipher-stored the way our batch
data already is. Varaha stores this stuff in plaintext; we won't.

---

## TIER 1 — Integrity-critical (a credit is not defensible without these)

### 1. Application-site registry: land parcel + boundary + owner + consent  🔴 HIGH
- **Varaha has:** `farmers` table (KYC, `farmer_consent`, FPIC signature + "holding consent" photo),
  `site` table with `boundary` (WKT polygon) + `boundary_method` + overlap check
  (`/nearest-farm-boundary/`, "boundary is overlapping with existing site"). Screens: SiteBoundary,
  AddFarmer, SelectFarmer, FPIC read/upload/signature.
- **Why a dMRV needs it:** biochar C-sink permanence & **no-double-counting** require knowing
  *where* the biochar was applied (a mapped parcel), *who* controls that land, and documented
  *consent*. Registries (CSI, Puro, Verra soil) expect application-site traceability + a landowner
  agreement. Right now a batch's `EndUseApplication` has a point (`lat/long`) + a farmer photo but
  no parcel, no owner identity, no consent artifact — that won't survive audit.
- **We have today:** `EndUseApplication {lat, long, farmerPhotoPath, farmerPhotoSha256, buyerName,
  buyerContact, deliveredAmountKg}`. Point-only, no boundary, no registry, no consent.
- **Adapt:**
  1. New `ApplicationSite` table: `siteUuid, ownerName, ownerContact, boundaryGeoJson,
     boundaryMethod (gps_walk|draw), areaHa, centroidLat/Lng, consentSignatureSha256,
     consentDocSha256, createdAt, deviceSig`.
  2. New screen **Boundary Capture** (walk-the-perimeter GPS polygon; reuse `location_service.dart`
     + `sensors_plus` for the same anti-spoof metadata you already collect). Compute area, store GeoJSON.
  3. New screen **Consent** — reuse the Ed25519 signer for a signed consent record + a "farmer
     holding consent" secure photo. No plaintext PII beyond what the methodology needs.
  4. Overlap/dup guard: before save, query backend for nearby registered boundaries (adapt Varaha's
     `nearest-farm-boundary`) → reject overlaps → prevents two operators crediting the same field.
  5. Link `EndUseApplication.siteUuid → ApplicationSite`.
- **Plugs into:** `lib/ui/screens/end_use_application_screen.dart`, `lib/data/local/tables.dart`,
  `location_service.dart`, `crypto_signer.dart`; backend new `POST /api/v1/application-site`.

### 2. Verification round-trip: reviewer → field recapture loop  🔴 HIGH
- **Varaha has:** `media.verification_status` + `verification_remarks` written by the server;
  the app surfaces reviewer decisions; operator recaptures rejected evidence.
- **Why a dMRV needs it:** this *is* the "V" in MRV. A verifier must reject bad/blurred/spoofed
  evidence and the field operator must see the reason and recapture. Without the loop, a rejected
  batch is a dead end and the reviewer has no lever.
- **We have today:** a web portal (`backend/portal`) + `/compliance` endpoint (reviewers exist),
  but **no in-app "your batch/photo was rejected → recapture" flow**. Status is one-way (upload).
- **Adapt:**
  1. Add `verificationStatus (PENDING|APPROVED|REJECTED|NEEDS_INFO)` + `reviewerRemarks` +
     `reviewedAt` to batch and to each media/proof row.
  2. `sync_queue_manager` pulls verification decisions on sync (new `GET /api/v1/batches/{uuid}/review`).
  3. Dashboard gets a **"Needs Attention"** section (adapt Varaha's shipment-detail + LocalTasks);
     tapping opens the exact step to recapture; recapture re-signs + re-queues.
- **Plugs into:** `dashboard_screen.dart`, `sync_health_screen.dart`, `proof_wallet_screen.dart`,
  `sync_queue_manager.dart`; backend review endpoint + portal action.

### 3. Methodology & version governance: forced update + server-driven config  🔴 HIGH
- **Varaha has:** Firebase Remote Config (`whats_new`, version/feature gating), in-app updates,
  WhatsNew screen.
- **Why a dMRV needs it:** you must **not** let a stale app (old emission factors, old LCA
  constants, old positive-list) mint credits. Min-version enforcement + a server-pinned
  `methodology_version` stamped on every batch = credit integrity + a clean audit trail of which
  standard version produced which credit.
- **We have today:** none (confirmed). Emission factors live in `backend/lca_engine.py` (good, one
  source of truth) but the client has no version gate and batches don't record the methodology version.
- **Adapt:**
  1. `GET /api/v1/config` → `{min_app_version, methodology_version, feedstock_positive_list[],
     emission_factors{}, csi_standard_version}`; fetch at launch, cache in SQLCipher.
  2. Hard block (or soft-warn) below `min_app_version`; a lightweight **Update Required** screen
     (adapt WhatsNew).
  3. Stamp `methodologyVersion` + `csiStandardVersion` onto `SystemMetadata` per batch.
- **Plugs into:** `main.dart` bootstrap, `api_base.dart`, new `config_provider`; a tiny
  `update_required_screen.dart`.

### 4. Server-driven master data: kiln registry, feedstock positive-list, emission factors  🔴 HIGH
- **Varaha has:** synced lookups (country/state/district/block/village/bank), kiln list, facility
  list — all server-driven, cached locally.
- **Why a dMRV needs it:** kilns must be **pre-registered/approved** (you already have a `kilns`
  table + `/admin/kiln`), feedstock must come from an **approved positive-list**, and emission
  factors change with methodology revisions. Hardcoding = an app release per methodology change +
  unverifiable kiln IDs.
- **We have today:** `kiln_select_screen` and `lantana_sourcing` likely use local/hardcoded lists;
  backend has `kilns` + `emission_factors.py` but the client doesn't sync them.
- **Adapt:** cache tables `RegisteredKiln`, `FeedstockSpecies`, `EmissionFactor` synced from
  `/config` (or dedicated endpoints); `kiln_select` and `lantana_sourcing` pick from the **approved
  synced list**; bind `PyrolysisTelemetry.kilnId` to a registered kiln.
- **Plugs into:** `kiln_select_screen.dart`, `lantana_sourcing_screen.dart`,
  `lantana_sourcing_notifier.dart`, `pyrolysis_writer.dart`.

### 5. Instrument-calibration linkage (scale + thermocouple)  🔴 HIGH
- **Varaha analogue:** — (Varaha doesn't do this; it's a CSI requirement your backend already
  models via `scale_calibrations`). Included because it's dMRV-essential and currently unlinked.
- **Why a dMRV needs it:** CSI requires measurements from **calibrated, in-date** instruments.
  Your BLE scale + thermocouple readings currently aren't tied to a valid calibration record.
- **We have today:** `scale_calibrations` + `/admin/scale-calibration` on backend; BLE services on
  client; no linkage.
- **Adapt:** on batch create, resolve the active calibration for the paired scale/thermocouple
  (by device MAC / instrument id), stamp `scaleCalibrationId` + `thermocoupleCalibrationId` onto the
  batch, and **block/flag** if calibration is missing or expired.
- **Plugs into:** `yield_scale_notifier.dart`, `pyrolysis_ble_notifier.dart`,
  `ble_weight_scale_service.dart`, `ble_temperature_service.dart`.

---

## TIER 2 — Mass balance & chain-of-custody (anti over-crediting)

### 6. Mass-balance reconciliation: biomass in → biochar out → distributed  🟠 MED-HIGH
- **Varaha has:** `biomass_input` (intake weight+moisture), `biomass_dispatch`/`biochar_dispatch`
  (weights at each hop), `dispatch_sites`. It tracks mass through the chain.
- **Why a dMRV needs it:** prevents crediting more biochar than the biomass could yield and catches
  **over-distribution** (Σ delivered > produced) — a classic fraud/error. CSI expects mass balance.
- **We have today:** per-batch `BiomassSourcing.biomassInputKg`, `YieldMetrics` (wet/dry),
  `EndUseApplication.deliveredAmountKg`, composite QR custody. The pieces exist but nothing
  reconciles them.
- **Adapt:** a **Reconciliation** view per batch (and per operator/period): biomass in → yield
  (with plausibility band vs feedstock yield factor) → Σ distributed; hard-flag when
  `Σ delivered > dryYield` or yield is implausible for the input. Surface on dashboard.
- **Plugs into:** `dashboard_stats_provider.dart`, `proof_queries.dart`, new reconciliation widget.

### 7. Transport custody detail (vehicle + driver + photo)  🟠 MED
- **Varaha has:** driver name/phone, truck number, truck front/back photo, invoice upload per hop.
- **Why a dMRV needs it:** transport emissions (you already use `transport_distance_km` in the LCA)
  plus **custody** of the biochar between production and application.
- **We have today:** `TransportEvent` + `transport_distance_km`; likely no vehicle/driver/photo.
- **Adapt:** enrich `TransportEvent` with `vehicleId, driverName, driverContact, custodyPhotoSha256`
  (reuse `secure_capture_service`).
- **Plugs into:** transport flow + `secure_capture_service.dart`.

---

## TIER 3 — Program-scale operations & UX (not integrity-critical, but expected at scale)

### 8. Draft / resume + unsynced-loss guard  🟡 MED
- **Varaha has:** explicit Draft state, "N items unsynced", *"logging out will lose unsynced media —
  sync first?"* guard.
- **We have today:** `SyncOutbox` + `sync_health_screen` + `wipe_context.dart`. Likely missing
  resumable half-finished batches and a wipe/logout guard when the outbox is non-empty.
- **Adapt:** persist in-progress batch as a resumable draft; block device wipe / re-enroll while
  `SyncOutbox` has PENDING rows (tie into `wipe_context.dart`); show a draft list.
- **Plugs into:** `batch_session_notifier.dart`, `sync_health_screen.dart`, `wipe_context.dart`.

### 9. In-app supervisor visit + day-start liveness  🟡 MED
- **Varaha has:** Day-Start Audit (start-of-day site image + video); (your backend already has
  `supervisor_visits` + `operator_training`).
- **Why useful:** liveness/attendance anti-fraud (site active that day) + closes the loop on the
  supervisor apparatus your backend already exposes.
- **Adapt:** a **Supervisor Visit** capture screen (feeds `/admin/supervisor-visit`) and an optional
  **Day-Start check-in** (GPS + photo/video) gating batch creation for the day.
- **Plugs into:** new screens; existing secure-capture + location services.

### 10. Program dashboard KPIs + live credit estimate  🟡 LOW-MED
- **Varaha has:** dashboard KPIs (biomass today/week/month, cycle counts).
- **Adapt (and surpass):** you have the LCA engine — show **estimated t CO₂e this batch / this
  period**, pending-verification count, mass-balance status, calibration-expiry warnings. This is a
  place you can beat Varaha, not just match it.
- **Plugs into:** `dashboard_provider.dart`, `dashboard_stats_provider.dart`.

---

## Screen shopping list (new Flutter screens to add)

| New screen | Adapted from Varaha | Tier |
|---|---|---|
| Boundary Capture (GPS polygon) | SiteBoundaryScreen | 1 |
| Applicant / Land-owner + Consent | AddFarmer + FPIC signature | 1 |
| "Needs Attention" verification queue | Shipment/LocalTasks + media verification | 1 |
| Update Required / What's New | WhatsNewScreen + version gate | 1 |
| Kiln picker from approved registry | AddKiln/KilnDetails/kiln list | 1 |
| Mass-balance reconciliation | FacilityManagerHome stats + dispatch | 2 |
| Supervisor Visit / Day-Start check-in | Day-Start Audit | 3 |

## What NOT to copy from Varaha
- Its **plaintext SQLite**, **cleartext traffic**, shipped **network inspector**, and **test APM
  endpoint** — your SQLCipher + Ed25519 + freeRASP posture is strictly better; keep it.
- Its **payments/KYC breadth** (Aadhaar/UPI/MFS bank capture) — only relevant if you actually pay
  farmers in-app. Skip unless the program requires it; if so, capture the *minimum* PII, signed.
- Its multi-role/multi-tenant facility-admin surface — overkill for a device-per-operator model
  unless you scale to shared devices.

---

## Suggested sequence
1. **Config + version gate + master-data sync** (#3, #4) — small, unblocks everything, protects credit integrity immediately.
2. **Calibration linkage** (#5) — cheap, high audit value, backend already there.
3. **Verification round-trip** (#2) — activates your existing portal/reviewers.
4. **Application-site + consent + boundary** (#1) — the big one; largest new surface.
5. **Mass-balance** (#6), then Tier-3 polish.
