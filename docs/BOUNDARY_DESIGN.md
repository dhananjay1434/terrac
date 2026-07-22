# Boundary + Overlap — exact design for OUR stack

How to build source-parcel boundaries + anti-double-count overlap on
TerraCipher: **FastAPI/SQLAlchemy-async + Postgres (Render), Flutter +
Drift/SQLCipher, React portal**, reusing our Ed25519 + outbox + geo.py
corroboration. Verified against current code: Postgres (fail-loud DATABASE_URL),
**no spatial libs yet**, `Batch` has `latitude/longitude` + `project_id`, geo.py
already does haversine GPS corroboration + quarantine.

## Decision (from prior turns, locked)
- Boundary = the **biomass source parcel** (not the kiln/facility, not the
  deployment area). Registered **once in the portal at project setup**.
- The phone keeps doing what it already does well (GPS-tagged, hashed, signed
  photos); the backend checks each capture is **inside** the registered parcel.
- Anti-double-count = **overlap rejection** when a new parcel is registered.
- Kill the current **fake stub** (`captureGpsPolygon()` persists a boolean) —
  it's a false attestation.

---

## 1. Geometry: how to store + compute WITHOUT a DB extension (MVP), PostGIS later

We have plain Postgres, no PostGIS. Two options:

- **MVP (recommended): `shapely` in Python.** Store the polygon as **GeoJSON
  text** (JS-native for the portal) in a normal `TEXT` column; do all geometry
  (validity, area, overlap, point-in-polygon) in Python with `shapely`. No DB
  extension, portable, trivially unit-testable. Add `shapely` to
  `requirements.txt`.
- **Scale upgrade (later): PostGIS.** Render Postgres supports `CREATE EXTENSION
  postgis`; add a `geometry`/`geography` column + GIST index + `ST_Intersects`/
  `ST_Area`/`ST_Contains`. Do this only when parcel counts make the O(n) overlap
  scan slow.

**Avoiding O(n²) without PostGIS:** store a **bounding box** (`min_lat, min_lon,
max_lat, max_lon`) per parcel. On registration, SQL-prefilter to parcels whose
bbox overlaps the new one (a cheap indexed range query), then run the exact
shapely overlap only on those few candidates. This gives you 90% of a spatial
index with zero extension.

---

## 2. Backend data model (new `source_parcel` + `Batch.parcel_uuid`)

New table `source_parcel` (Alembic migration, mirror existing patterns in
`alembic/versions/`):
```
parcel_uuid    (PK, uuid)
project_id     (FK → project; scopes overlap checks + tenancy later)
name           (text)
boundary_geojson (text)          -- canonical polygon
area_m2        (float)           -- server-computed from the polygon (shapely)
declared_area_acres (float,null) -- what the operator claimed (area-mismatch check)
bbox_min_lat / bbox_min_lon / bbox_max_lat / bbox_max_lon (float)  -- prefilter
boundary_method (text)           -- 'portal_drawn' | 'field_walk' | 'imported'
boundary_status (text)           -- 'approved' | 'pending_review' | 'rejected'
created_by_user_id (fk portal user)   -- who registered it (audit)
created_at     (timestamptz)
-- optional later: signature (HMAC/Ed25519 over the canonical geojson)
```
Add to `Batch`: `parcel_uuid` (FK, **nullable** so existing batches grandfather
in). Batches reference the parcel; the polygon lives here once, reused by all
batches from that parcel.

---

## 3. Overlap check (anti-double-count) — the core, at registration

Portal POSTs the drawn polygon → backend `POST /api/v1/portal/parcels`
(`require_role("admin")`, same gate as issue-credit). Before insert:

1. **Validity** — `shapely.geometry.shape(geojson)`; reject if `not poly.is_valid`
   or `< 3` distinct vertices → `boundary_invalid`.
2. **Area** — compute `area_m2` (project to an equal-area CRS or use a geodesic
   area; `shapely` + a simple UTM/`pyproj` transform, or the spherical-excess
   formula). If `declared_area_acres` is given and differs > tolerance (e.g.
   ±15%) → flag `area_mismatch` (Varaha's "Area mismatch Detected").
3. **Overlap** — bbox-prefilter approved parcels (SQL), then for each candidate:
   `overlap = new.intersection(existing).area / new.area`. If
   `overlap > OVERLAP_TOLERANCE` (start ~1% to allow GPS jitter at edges) →
   **reject** `boundary_overlaps_existing_parcel` (or route to
   `pending_review`). This is the double-counting defense.
4. On success → store (status `approved`), return the parcel.

Env-gate the strictness (`DMRV_PARCEL_OVERLAP_ENFORCED`, default on) exactly
like we did for `DMRV_REQUIRE_EXIF_GPS`, so a demo/edge case can relax without a
code change.

---

## 4. Corroboration: extend geo.py to point-in-polygon (reuses GPS we ALREADY capture)

`geo.py` already anchors a batch on photo EXIF GPS + haversine + quarantine.
Extend `_evaluate_anchor` (and/or the batch corroboration path): **if the batch
has a `parcel_uuid`**, load the parcel polygon and check the capture's GPS is
inside it:
```
inside = parcel_poly.buffer(GPS_TOLERANCE_DEG).contains(Point(lon, lat))
```
- Buffer the polygon by a small tolerance (~20–30 m, converted to degrees, or a
  projected buffer) to allow honest GPS drift at the edge.
- Outside → new sibling status **`QUARANTINE_GPS_OUTSIDE_PARCEL`** (safe: we
  verified status strings are consumed loosely; mirror the existing
  `QUARANTINE_GPS_MISMATCH`/`_MISSING`). Surface the reason in the portal.
- **This needs NO new mobile capture** — the phone already stamps + signs EXIF
  GPS. That's the efficiency: boundary corroboration rides existing evidence.

Net corroboration ladder (strongest to weakest): signed request → SHA-256 photo
→ EXIF GPS present → GPS matches batch point (existing) → **GPS inside approved,
non-overlapping parcel (new)**.

---

## 5. Portal (registration UI) — no Google key needed

- Add a **Boundary** step to project/site registration (extend `Registry.tsx`
  or a new Projects page). Use **Leaflet + OpenStreetMap tiles** (free, no API
  key — unlike Varaha's Google Maps) with **leaflet-draw** to draw the polygon;
  also accept **paste GeoJSON / import KML** for survey data.
- On submit → POST GeoJSON → show the backend's result inline: approved, or
  **"overlaps existing parcel"** / "area mismatch" with the offending overlap
  highlighted. Role-gated server-side (`require_role("admin")`).
- Self-contained + CSP-friendly (Leaflet inlines cleanly).

---

## 6. App (mobile) — minimal change + kill the fake

Because the parcel is **portal-owned**, the app change is small:
- **Remove the fake** `captureGpsPolygon()` boolean theatre from
  `lantana_sourcing_notifier.dart` / `lantana_sourcing_screen.dart`.
- Instead, the batch **references a `parcel_uuid`** (selected/assigned for the
  project). The sourcing screen can show the registered parcel read-only ("Source
  parcel: <name>, approved") — honest, no false capture.
- No Drift geometry needed for MVP (polygon lives server-side). A Drift v25→v26
  migration only adds `parcel_uuid` to the batch/outbox payload.

**Phase 2 (optional, the "authorized field-walk link" you raised):** portal mints
a scoped, **Ed25519-signed, single-use link** (same machinery as our enrollment
token) → Android App Link / iOS Universal Link → opens the app to a "walk this
parcel" task → operator walks, app records GPS vertices → uploads via the
existing **outbox** → parcel `boundary_method='field_walk'`. The app verifies the
link **offline** with our public key (we already do this for signed requests).
This upgrades a *declared* boundary to a *ground-truthed, authorized* one.

---

## 7. Migrations & rollout
- **Alembic**: create `source_parcel`; add nullable `Batch.parcel_uuid`.
- **Grandfather**: existing batches (`parcel_uuid` null) → corroboration skips
  the polygon check (keeps old data valid); new batches require a parcel once
  the project has one.
- **Drift** v25→v26: add `parcel_uuid` to the batch record + outbox payload
  (tiny).

## 8. Tests (mirror our existing style)
- **Backend (pytest + shapely fixtures):** overlapping polygons → reject;
  disjoint → accept; self-intersecting → `boundary_invalid`; area-mismatch flag;
  point-in-polygon inside → ok, outside → `QUARANTINE_GPS_OUTSIDE_PARCEL`; buffer
  edge case; env-gate off → relaxed. Extend `test_gps_corroboration.py`.
- **Portal (vitest):** draw→submit→approved; overlap→rejection reason rendered;
  role-gating.
- **App (flutter):** batch carries `parcel_uuid`; the fake polygon path is gone
  (regression guard that `captureGpsPolygon` no longer persists a boolean).

## 9. Why this beats Varaha on our stack
Varaha: field-drawn boundary + server overlap (good, but the boundary and the
evidence are both *unsigned*, and PII/geometry sit in a *plaintext* DB). Ours:
**portal-controlled registration + overlap rejection + every field photo's
Ed25519-signed, SHA-256-anchored GPS checked point-in-polygon** against the
approved, non-overlapping parcel — i.e. not just "a boundary exists" but "signed
evidence proven inside the sanctioned land." Same table-stakes feature, turned
into an integrity differentiator, with **no Google Maps key** and **no new
mobile capture** for the MVP.

## 10. Suggested build order
1. Backend `source_parcel` + overlap check + `Batch.parcel_uuid` (shapely, bbox
   prefilter) — the anti-double-count core.
2. Extend geo.py point-in-polygon corroboration (reuses existing GPS).
3. Portal Leaflet draw/import + registration UI.
4. Kill the app fake stub; add `parcel_uuid` reference.
5. (Later) Phase 2 authorized field-walk link; (later) PostGIS when scale needs.
