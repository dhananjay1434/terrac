# dMRV Intelligence Plan
**Source:** Red-team reverse engineering of Bluelayer (3-layer platform) + Varaha Kalki (APK).  
**Purpose:** Exact specification of what to add to this codebase, and where. No code was changed.

---

## Reading Guide

Each item tells you:
- **File** — exact path relative to `flutter_dmrv/`
- **Where** — line number or anchor string to insert after
- **What** — what to add, with the field names, types, and rationale

Priority tiers:
- 🔴 **P0** — Blocks credit issuance. Do these first.
- 🟡 **P1** — Required for Rainbow Standard (10× credit price). Do these second.
- 🟢 **P2** — Operational efficiency / Varaha parity. Do when the above are done.

---

## P0 — CSI Export Endpoint (Blocks Credit Issuance)

### What Bluelayer taught us
Bluelayer's CSI registry integration calls `GlobalCSinkVerificationReport` — a precise JSON payload that the Carbon Standards International (CSI) registry ingests to mint credits. Your backend does **not** have this endpoint. Without it you cannot submit to CSI.

### What your backend already has (do NOT re-add)
- `Batch.lab_h_corg` column (migration `c3d4e5f6a7b8`)
- `Batch.organic_carbon_pct` column (migration `c9d0e1f2a3b4`)
- `POST /api/v1/admin/lab-hcorg` and `POST /api/v1/admin/lab` — lab ingestion
- `LCAAudit` dataclass with all 8 LCA steps
- `batch.lca_audit_json` — the full LCA audit stored as JSON on each batch

### Add: CSI export endpoint

**File:** `backend/server.py`  
**Where:** After line 2435 (`return compliance_view(batch)`), before line 2438 (`# P2.0 — Lab & Verifier portal seam`)

Add a new endpoint:

```python
@app.get("/api/v1/batches/{batch_uuid}/csi_export")
async def batch_csi_export(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
```

The endpoint should:
1. Call `_require_admin(x_admin_secret)` — same auth as `/compliance`
2. Load the `Batch` row by `batch_uuid`
3. Parse `batch.lca_audit_json` (it's a JSON string of `LCAAudit.__dict__`)
4. Return a JSON dict shaped as `GlobalCSinkVerificationReport`:

```
producer_id          = batch.project_id  (or "UNLINKED" if None)
project_id           = batch.project_id
product_quantity_dm  = lca["dry_mass_t"] * 1000          # kg dry mass
gross_amount_of_co2  = lca["gross_c_sink_t_co2e"]        # tCO2e
c_content            = (batch.organic_carbon_pct or 0.55) * 100  # as %, e.g. 55.0
h_corg_ratio         = batch.lab_h_corg                   # None → warning
fossil_fuel_emissions = lca["transport_penalty_kg"] / 1000  # tCO2e
methane_emissions     = lca["ch4_penalty_kg"] / 1000        # tCO2e
certification_id      = str(batch.batch_uuid)
certification_date    = batch.received_at.date().isoformat()
matrix_of_sink        = "biochar"
gps_geolocation_of_sink_latitude  = batch.latitude
gps_geolocation_of_sink_longitude = batch.longitude
declaration_feedstock_positive_list = True
declaration_permanence_tested       = batch.lab_h_corg is not None
declaration_additionality           = True
```

Also include a top-level `_meta` block:
```
_meta.provisional = batch.provisional
_meta.issuable    = not batch.provisional
_meta.methodology = batch.lca_methodology_version
_meta.warnings    = list of strings (e.g. "h_corg_ratio not lab-measured" if lab_h_corg is None)
```

Return 200 even when provisional — include warnings so a project developer can preview.  
Return 404 `unknown_batch` if batch not found.  
Return 400 `invalid_batch_uuid` if UUID parse fails.

**CSI field reference:** All required fields above come from Bluelayer's `GlobalCSinkVerificationReport` schema (extracted from `openapi_spec_0.json`, lines 12,400–12,600 approx).

---

## P0 — Rainbow BiCRS Export Endpoint

### What Rainbow Standard requires (and why it matters)
Rainbow (formerly Riverse) is ICVCM CCP-eligible as of March 2026. Credits sell for **$100–300/tonne** vs CSI's $5–30/tonne. You need only **one extra field** beyond CSI: `h_corg_ratio` (already in DB). The Rainbow "Distributed Closed-Kiln Biochar" methodology matches your field setup exactly.

### Add: Rainbow export endpoint

**File:** `backend/server.py`  
**Where:** Immediately after the CSI export endpoint you add above.

```python
@app.get("/api/v1/batches/{batch_uuid}/rainbow_export")
async def batch_rainbow_export(
    batch_uuid: str,
    x_admin_secret: str = Header(..., alias="X-Admin-Secret"),
    session: AsyncSession = Depends(get_session),
):
```

The endpoint should return a JSON dict shaped as Rainbow BiCRS submission:

```
batch_id                = str(batch.batch_uuid)
project_id              = batch.project_id
methodology             = "Distributed-Closed-Kiln-Biochar"
feedstock_type          = batch.feedstock_species
pyrolysis_min_temp_c    = batch.min_recorded_temp_c
biochar_dry_yield_kg    = lca["dry_mass_t"] * 1000
h_corg_ratio            = batch.lab_h_corg           # REQUIRED for Rainbow — null = not eligible
organic_carbon_pct      = batch.organic_carbon_pct   # from lab
carbon_mass_balance_net_t_co2e = batch.net_credit_t_co2e
production_gps_lat      = batch.latitude
production_gps_lon      = batch.longitude
batch_date              = batch.received_at.date().isoformat()
transport_distance_km   = batch.transport_distance_km
moisture_percent        = batch.moisture_percent

# Rainbow-specific compliance signals
lab_h_corg_certified    = batch.lab_h_corg is not None
c10_compliant           = not batch.provisional
provisional_reasons     = json.loads(batch.provisional_reasons or "[]")

# Rainbow eligibility gate
rainbow_eligible        = (
    batch.lab_h_corg is not None
    and not batch.provisional
    and batch.latitude is not None
    and batch.min_recorded_temp_c > 190.0
)
```

If `rainbow_eligible` is False, include `rainbow_blockers` — a list of human-readable strings explaining what's missing.

---

## P0 — Portal: Add Export Links to Batch Detail

Bluelayer's portal exposes download buttons for each registry format directly from the batch detail page. Your portal currently returns batch data but no export links.

**File:** `backend/portal/routes.py`  
**Where:** Inside the `GET /batches/{batch_uuid}` handler (line 191), in the response dict it returns.

Add two fields to the response:
```python
"csi_export_url":     f"/api/v1/batches/{batch_uuid}/csi_export"
"rainbow_export_url": f"/api/v1/batches/{batch_uuid}/rainbow_export"
```

These are just URL strings — the admin uses the X-Admin-Secret header when calling them directly. This lets any portal UI render clickable export buttons without knowing the endpoint paths.

---

## P1 — Flutter: Lab Pending Status Banner

### Gap
After a batch is closed (EndUseApplicationScreen), the operator has no way to see whether lab results have been submitted for that batch. In Bluelayer, every batch card shows a colour-coded status pill (Provisional / Lab Pending / Issuable). In Varaha Kalki, each cycle shows a sync status badge.

### Add: Lab status field to local schema

**File:** `lib/data/local/tables.dart`  
**Where:** After line 50 (end of `SystemMetadata` table class, inside the class body — NOT inside `primaryKey`). The schema version comment at line 41 mentions v22 as latest. This would be **v24** (v23 is the project_id/scale_id linkage).

Add a new column to `SystemMetadata`:
```dart
// v24: lab result status received from server on sync.
// Values: 'pending' | 'partial' | 'complete'
// 'pending'  = no lab results ingested yet for this batch
// 'partial'  = h_corg OR organic_carbon_pct received but not both
// 'complete' = both h_corg AND organic_carbon_pct confirmed by server
TextColumn get labResultStatus =>
    text().withDefault(const Constant('pending'))();

// Net credit estimate from the most recent server sync (tCO2e).
// Zero until at least one sync has returned a credit value.
RealColumn get netCreditTCo2e =>
    real().withDefault(const Constant(0.0))();

// True when server has confirmed this batch is issuable (not provisional).
BoolColumn get issuable =>
    boolean().withDefault(const Constant(false))();
```

**File:** `lib/data/local/app_database.dart`  
**Where:** Inside `onUpgrade`, add a new `if (from < 24)` block after the existing `if (from < 23)` block:
```dart
if (from < 24) {
  await m.addColumn(systemMetadata, systemMetadata.labResultStatus);
  await m.addColumn(systemMetadata, systemMetadata.netCreditTCo2e);
  await m.addColumn(systemMetadata, systemMetadata.issuable);
}
```
Also increment `schemaVersion` from `22` to `24` (if v23 is already applied, check the current value first).

### Add: Sync pulls lab status from server

**File:** `lib/services/sync_queue_manager.dart`  
**Where:** After each successful sync of a batch's outbox rows, make a `GET /api/v1/batches/{batch_uuid}/compliance` call and update the local `SystemMetadata` row with `labResultStatus`, `netCreditTCo2e`, and `issuable`.

The compliance response already returns `provisional`, `issuable`, and `reasons`. Map like this:
```
if reasons contains "assumed_h_corg" AND "assumed_corg" → labResultStatus = 'pending'
if reasons contains only one of them                    → labResultStatus = 'partial'
if neither "assumed_h_corg" nor "assumed_corg" in reasons → labResultStatus = 'complete'
issuable    = response["issuable"]
netCreditTCo2e = (parse from lca_audit_json if available, else leave unchanged)
```

The compliance endpoint is admin-authenticated. You have two options:
- **Option A:** Add a new public (device-token-authenticated) GET endpoint `GET /api/v1/batches/{batch_uuid}/status` that returns just `{issuable, provisional, lab_status, net_credit_t_co2e}` — no X-Admin-Secret required.
- **Option B:** The portal already has `GET /api/v1/portal/batches/{batch_uuid}` (line 191 in portal/routes.py) which is session-authenticated. The app could call this via a stored portal token.

**Recommendation: Option A** — add the lightweight status endpoint to `backend/server.py`, device-token-authenticated (same as the existing `/api/v1/telemetry` pattern), returning only the 4 non-sensitive fields listed above.

### Add: Status banner in ProofWalletScreen

**File:** `lib/ui/screens/proof_wallet_screen.dart`  
**Where:** Inside the `build` method, above the batch list. Currently at line 20 the screen just watches `cryptographicReceiptsProvider`. 

For each receipt card, add a coloured status row below the SHA-256 hashes section:

```
if labResultStatus == 'pending'  → amber pill "LAB PENDING"
if labResultStatus == 'partial'  → amber pill "LAB PARTIAL"
if labResultStatus == 'complete' → green pill  "LAB ✓"
if issuable == true              → green pill  "ISSUABLE — X.XX tCO₂e"
if issuable == false             → grey text   "Provisional — pending lab"
```

This mirrors exactly what Bluelayer shows on their batch cards (from the `projects-*.js` bundle analysis).

---

## P1 — Flutter: Biomass Input Screen Gap

### Gap
Rainbow Standard requires the **biomass input amount** (kg of biomass fed into the kiln) — mandatory for the C1 carbon mass balance check. Your schema already has `biomassInputKg` and `biomassMeasurementMethod` on `BiomassSourcing` (added in v17). But the Lantana Sourcing screen needs to capture it.

**File:** `lib/ui/screens/lantana_sourcing_screen.dart`  
**Where:** Before the SAVE/COMMIT button.

Add two input fields:
1. `biomassInputKg` — numeric field, label "Biomass Fed to Kiln (kg)", required
2. `biomassMeasurementMethod` — dropdown with options `'direct_weigh'` and `'yield_conversion'`

These map directly to the existing `BiomassSourcing` Drift columns. The writer in `lib/data/local/yield_end_use_writers.dart` (or equivalent sourcing writer) needs to include them in the `BiomassSourcingCompanion`.

---

## P1 — Flutter: Composite Sample Screen — Kiln QR Scan

### Gap
Rainbow C4 requires the composite pile sub-sample to be tagged with both the **kiln QR** and **batch QR**. Your `CompositePileSamples` table (v20) has `kilnQr` and `batchQr` columns, but `composite_sample_screen.dart` may not yet capture them.

**File:** `lib/ui/screens/composite_sample_screen.dart`  
**Where:** The form that captures sample GPS + photo.

Add:
1. A QR scanner widget for `kilnQr` — scan the kiln's physical QR label
2. Auto-fill `batchQr` from the active `batchSessionProvider` UUID (no scan needed — it's always the current batch)

If the kiln QR scanner is not already present, use the `mobile_scanner` package (already likely in `pubspec.yaml` given the kiln_select_screen exists).

---

## P1 — Backend: Alembic Migration for CSI Export Tracking

Bluelayer tracks each registry submission as a discrete event (Puro batch submission, Isometric statement, CSI GlobalReport). You should do the same — it lets you avoid duplicate submissions and gives auditors a trail.

**Create new file:** `backend/alembic/versions/e2f3a4b5c6d7_csi_export_log.py`

```sql
-- New table: registry_submissions
CREATE TABLE registry_submissions (
    id          SERIAL PRIMARY KEY,
    batch_uuid  UUID NOT NULL,
    registry    TEXT NOT NULL,           -- 'CSI' | 'Rainbow' | 'Puro' | 'Isometric'
    exported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    exported_by TEXT,                    -- admin email or 'api'
    payload_sha256 TEXT,                 -- SHA-256 of the submitted JSON
    status      TEXT DEFAULT 'exported'  -- 'exported' | 'submitted' | 'confirmed'
);
CREATE INDEX idx_registry_submissions_batch ON registry_submissions(batch_uuid);
```

The CSI export endpoint you add in P0 should INSERT a row here on every call (so you have a log). Add a `?record=true` query param to make logging opt-in if you prefer.

---

## P2 — Varaha Gap: Artisan Summary Screen

### What Varaha does
Varaha's `artisanal_summary` table (`facilityId, cycleDate, totalCycles, totalKilns`) powers a per-facility aggregate view. Operators see their week/month totals without scrolling individual batches.

### What to add to your Flutter app

**Create new file:** `lib/ui/screens/artisan_summary_screen.dart`

It should show per-device stats:
- Total batches completed (count from `SystemMetadata` where `syncStatus = 'SYNCED'`)
- Total provisional vs issuable (from the `issuable` column you add in P1)
- Total estimated credits (sum of `netCreditTCo2e`)
- Last 7 days vs last 30 days toggle

No new DB table needed — aggregate from existing `SystemMetadata` rows using Drift's `COUNT`, `SUM`.

**File:** `lib/ui/screens/dashboard_screen.dart`  
**Where:** The dashboard stat boxes section (around line 66 `_buildStatBox`).

Add a new stat box: "CREDITS EARNED (est.)" showing the sum of `netCreditTCo2e` for issuable batches. Add a tap → navigates to `ArtisanSummaryScreen`.

---

## P2 — Varaha Gap: WhatsNew / Announcements

Varaha has `WhatsNewResponse` / `WhatsNewItem` served from its backend. When methodology changes, operators see a one-time modal with what's new.

**Backend:** Add `GET /api/v1/whats-new` returning:
```json
{
  "enabled": true,
  "items": [
    {
      "version": "2.1",
      "title": "Rainbow Standard Now Supported",
      "body": "Your batches now qualify for Rainbow BiCRS credits worth $100-300/tonne. Lab H:Corg results unlock eligibility.",
      "cta_label": "Learn More",
      "cta_url": "https://rainbow-standard.org"
    }
  ]
}
```
Initially hardcode the response in server.py; move to a DB table later.

**Flutter:** On app launch (in `main.dart` or after the first dashboard load), call this endpoint and show a `showDialog` with the latest item the user hasn't seen (track seen version in `SharedPreferences` with key `whats_new_seen_version`).

---

## P2 — Varaha Gap: Registry Config Linkage

Varaha's `facilities` table has `registry TEXT` and `registry_config_id INTEGER` — each facility is linked to a specific registry. Your app currently has no way for a device to know which registry its project submits to.

**Backend:** In `POST /api/v1/admin/kiln` (line 2131 in server.py), or via a new `PATCH /api/v1/admin/project/{project_id}` endpoint, add a `target_registry` field:
```
target_registry: 'CSI' | 'Rainbow' | 'Puro'
```

Store it on a new `projects` table (or as a column on the existing kiln row — kilns already reference `kiln_id` and projects can be linked via `project_id`).

**Flutter:** During the enrollment QR flow (`enrollment_screen.dart`), decode `target_registry` from the enrollment payload and store in `SharedPreferences`. The ProofWalletScreen and sync status screen use it to show "Your project targets Rainbow" or "Your project targets CSI".

---

## P2 — Backend: RBAC for Portal (Bluelayer Model)

Bluelayer uses 34 discrete permissions across admin/edit/read tiers. Your portal currently has a simple `role` column (presumably 'admin' | 'verifier' | 'viewer' based on `portal/auth.py`).

**File:** `backend/portal/auth.py`  
**File:** `backend/portal/routes.py`

Add a `require_role` decorator that accepts a list of allowed roles (it may already do this — check the implementation). Ensure the following role mapping:

| Route | Minimum Role |
|---|---|
| `GET /portal/batches` | `verifier` |
| `GET /portal/batches/{uuid}` | `verifier` |
| `GET /portal/media/{id}` | `verifier` |
| `POST /portal/login` / `/logout` | public |
| `POST /portal/enroll-token` | `admin` |
| `GET /api/v1/batches/{uuid}/csi_export` (new) | admin secret |
| `GET /api/v1/batches/{uuid}/rainbow_export` (new) | admin secret |

This matches Bluelayer's `admin:credit-transactions` / `edit:batches` / `read:reports` pattern simplified for your two-role setup.

---

## P2 — Security: GPS Corroboration Hardening (Bluelayer Finding #2)

Bluelayer's security flaw: `LocationProximity` trusts the device EXIF GPS — a rooted device can spoof it. Your app uses `mock_location_enabled` flag but this is self-reported by the device.

**Your corroboration.py already does server-side GPS cross-check** (comparing EXIF GPS from uploaded photo against the batch coordinates). This is better than Bluelayer.

**Hardening to add:**

**File:** `backend/server.py`  
**Where:** In the `recompute_batch_credit` function (around line 934), after the GPS corroboration check.

Add a new `provisional_reason`: `gps_delta_too_large` — if the haversine distance between `batch.latitude/longitude` and the photo EXIF GPS exceeds a threshold (e.g. 5 km), add this reason. Currently this may already exist — grep for `gps` in `corroboration.py`. If it does, this item is already done.

---

## Summary Table

| Priority | What | File | Notes |
|---|---|---|---|
| 🔴 P0 | CSI export endpoint | `backend/server.py` after line 2435 | Returns `GlobalCSinkVerificationReport` JSON |
| 🔴 P0 | Rainbow export endpoint | `backend/server.py` after CSI export | Returns Rainbow BiCRS submission JSON |
| 🔴 P0 | Portal export URLs | `backend/portal/routes.py` line 191 | Add `csi_export_url`, `rainbow_export_url` to batch detail response |
| 🟡 P1 | Lab status columns in Flutter | `lib/data/local/tables.dart` | Add `labResultStatus`, `netCreditTCo2e`, `issuable` to `SystemMetadata` |
| 🟡 P1 | Schema migration v24 | `lib/data/local/app_database.dart` | `onUpgrade` block for 3 new columns |
| 🟡 P1 | Sync pulls compliance status | `lib/services/sync_queue_manager.dart` | After batch sync, call `/compliance` or new `/status` endpoint |
| 🟡 P1 | Lab status banner in ProofWallet | `lib/ui/screens/proof_wallet_screen.dart` | Colour-coded pill per batch card |
| 🟡 P1 | Biomass input capture in UI | `lib/ui/screens/lantana_sourcing_screen.dart` | `biomassInputKg` + `biomassMeasurementMethod` fields |
| 🟡 P1 | Composite sample kiln QR | `lib/ui/screens/composite_sample_screen.dart` | QR scanner for kilnQr, auto-fill batchQr |
| 🟡 P1 | Registry submissions log table | new Alembic migration | `registry_submissions` table for audit trail |
| 🟢 P2 | Artisan summary screen | new `lib/ui/screens/artisan_summary_screen.dart` | Aggregate stats per device |
| 🟢 P2 | Dashboard credits stat box | `lib/ui/screens/dashboard_screen.dart` ~line 66 | Sum of `netCreditTCo2e` for issuable batches |
| 🟢 P2 | WhatsNew endpoint + Flutter modal | `backend/server.py` + `lib/main.dart` | Announcement on methodology changes |
| 🟢 P2 | Registry config linkage | `backend/server.py` + `lib/ui/screens/enrollment_screen.dart` | `target_registry` in enrollment payload |
| 🟢 P2 | Portal RBAC hardening | `backend/portal/routes.py` + `backend/portal/auth.py` | Verify role-gating on all portal routes |

---

## What NOT to Build (Bluelayer Traps)

Bluelayer built these and they add complexity without credit value for a field dMRV:

1. **Marketplace / Storefront layer** — Bluelayer has proposals, RFQ, channel listings, storefronts at portal.bluelayer.io. This is a credit *trading* layer. You don't need it until you have multiple buyers. Skip entirely.
2. **Generic AST formula engine** — Bluelayer uses a dynamic formula engine (vulnerable to circular-formula DoS). Your hardcoded `lca_engine.py` is safer, faster, and auditable. Do not generalize it.
3. **Credit issue/transfer/retire/withdraw ledger** — Bluelayer has a double-entry ledger with 5 account types. This is the registry's job, not yours. Your job is to produce the submission payload; the registry handles ledger state.
4. **God-object batch snapshots** — Bluelayer serializes the entire `ProjectModel` JSON on every version save. Your audit log (`lca_audit_json`) is already scoped correctly. Do not expand it.

---

*Generated from: Bluelayer OpenAPI spec (59 paths, 321 schemas), 95 JS page bundles, CSS design tokens, Varaha APK reverse engineering (6 analysis docs). Intelligence current as of 2026-07-11.*
