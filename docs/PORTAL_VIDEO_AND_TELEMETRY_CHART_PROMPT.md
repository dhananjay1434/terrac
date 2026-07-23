# Execution Prompt — Portal video playback + burn telemetry chart (one day)

**For the executing agent:** follow this literally, in order. Each PART is one commit, test-first,
three suites green before AND after. Additive only — **no DB migrations, no schema changes, no new
npm/pip dependencies.** Reuse the existing patterns named below. If reality differs from a
"VERIFIED CONSTRAINT," STOP and report — do not improvise.

## Scope (exactly this, nothing more)
1. Portal can **play videos** (quench / density / day-start walkthrough) — today they're captured,
   uploaded, and hash-verified, but the portal renders every media item with `<img>` so a video
   shows "Preview unavailable."
2. Portal shows the **thermocouple temperature curve** for a batch's burn (real data exists).
3. Portal shows the **post-burn yield weight** alongside it — **as a single labeled value, NOT a
   curve** (see the hard guardrail below).

## ⛔ HARD GUARDRAIL — do NOT fabricate a weight-vs-time curve
**VERIFIED CONSTRAINT:** there is **no weight time-series** anywhere in the system. The scale
(`yield_scale_notifier.dart`) keeps a 5-reading stabilization window **in memory only** and
persists a **single scalar** `wet_yield_weight_kg` (the post-burn biochar mass, measured once —
not a continuous signal like temperature). The DB, the payloads, and the API have **no** weight
series. Therefore:
- Plot the **temperature** curve from real data (`temperature_readings`).
- Show the **weight** as ONE number ("Post-burn yield: X kg"), a stat/marker next to the chart.
- **NEVER** synthesize, interpolate, or invent a weight time-series to draw a "curve." Drawing a
  line from fake weight points is exactly the kind of fabrication this project forbids. A real
  weight-over-time curve is a *separate future feature* (app must capture + persist a weight series
  during weighing) and is **out of scope for this task** — note it, don't build it.

## ⚠️ VERIFIED CONSTRAINTS (checked in code — rely on these)
- **No charting library in the portal** (`portal/package.json` has no recharts/chart.js/d3). Build
  the chart as **inline SVG** — no new dependency. (A new dep risks the build; don't add one.)
- Portal renders media `<img>`-only in `portal/src/components/EvidenceGallery/EvidenceGallery.tsx`
  (~line 170) and `portal/src/components/EvidenceLightbox/EvidenceLightbox.tsx` (~line 68).
- **A video detector ALREADY EXISTS — reuse it, do NOT create a new one.** `EvidenceGallery.tsx`
  (~line 24) has `function isVideo(m) { return /\.(mp4|mov|webm)$/i.test(m.filename ?? ""); }` and a
  working **"Videos" filter tab**. So the portal already *classifies* videos and lists them — it
  just still *renders* them with `<img>`. The gap is the render, not detection.
- **VERIFIED: real app videos carry a `.mp4` filename**, so `isVideo` fires for them. The app
  sandboxes video as `<uuid>.mp4` (`secure_capture_service.dart:464`), uploads via
  `MultipartFile.fromPath` (basename → `<uuid>.mp4`), and the backend stores `filename=file.filename`
  (`routers/media.py:211`). Detection works today; only the `<video>` render is missing.
- **`isVideo` is LOCAL to `EvidenceGallery.tsx` and NOT exported.** `EvidenceLightbox.tsx` does NOT
  import it. To branch in the lightbox you must **share** it (export `isVideo` and import it in the
  lightbox) — do not define a second, divergent copy.
- **`groupMedia` + `STEP_TITLES` are exported from `pages/BatchDetail.tsx`** and imported by the
  gallery. `groupMedia` keeps unknown capture-types (they fall to their raw name or
  `__unclassified__`), so a `_video` item **does** render — it is not dropped.
- **Gallery thumbnail uses `onLoad` + a `loaded` CSS class** (`className={loaded ? styles.loaded : …}`).
  `<video>` does **NOT** fire `onLoad` — it fires **`onLoadedData`**. If you copy the `<img>` pattern
  verbatim to `<video>`, `loaded` never becomes true and the thumbnail stays invisible. Use
  `onLoadedData={() => setLoaded(true)}` for the video branch.
- The media stream endpoint `backend/portal/routes.py::get_media` (`@router.get("/media/{operation_id}")`,
  ~line 1165) returns `media_type="application/octet-stream"` for everything.
- The batch-detail endpoint `backend/portal/routes.py::batch_detail`
  (`@router.get("/batches/{batch_uuid}")`, line 1029) returns `{batch, compliance, evidence_counts,
  media}` — it does **NOT** currently expose `temperature_readings`.
- Temperature series lives in `PyrolysisTelemetry.payload_json` → key `temperature_readings`
  (list of floats, one per minute), plus `min_temp`, `max_temp`, `burn_start_timestamp`,
  `burn_end_timestamp`.
- `BatchRow` in `portal/src/api.ts` already has `wet_yield_kg` (the scalar weight to display).
- Video capture types all end in `_video` (`quenching_video`, `density_video`,
  `day_start_walkthrough_video`); video files end in `.mp4`. Photos are `.jpg`.
- Portal tests: vitest + @testing-library. Mirror `EvidenceGallery.test.tsx` (exists). Backend
  tests: pytest; mirror `tests/test_portal_read.py` / `tests/test_portal_export.py` fixtures.

## PART PV-0 — Preflight (no code)
```
cd backend && python -m pytest -q            # record: all green
cd portal && npm test -- --run && npx tsc --noEmit && npm run build   # record: all green
```
If anything is red before you start, STOP and report — do not build on a red baseline.

---

## PART PV-1 — Backend: serve the correct media content-type
**Why:** so a video blob is typed `video/mp4` (helps `<video>` play) instead of octet-stream.

### Steps
1. In `backend/portal/routes.py::get_media`, compute `media_type` from the row before the
   `StreamingResponse`:
   - filename ends `.mp4` (case-insensitive) OR `row.capture_type` ends `_video` → `"video/mp4"`
   - filename ends `.jpg`/`.jpeg` → `"image/jpeg"`
   - else → `"application/octet-stream"` (unchanged default)
   Pass that as `media_type=`. Leave everything else (auth, traversal guard, streaming) untouched.
2. **Test** (`backend/tests/test_media_content_type.py`, new; mirror `test_portal_read.py`'s admin
   login + seeding): seed one media row with `filename="x.mp4"` (or a `_video` capture_type) and one
   with `filename="x.jpg"`; assert `GET /api/v1/portal/media/{op}` returns `Content-Type: video/mp4`
   and `image/jpeg` respectively. (If seeding media through the DB is simplest, insert a `MediaFile`
   row + write a tiny file via the storage layer, as `seed_demo.py` does.)
3. **CHECKPOINT:** new test green; full backend suite green.
**COMMIT:** `fix(backend): serve real media content-type (video/mp4, image/jpeg) not octet-stream`

---

## PART PV-2 — Portal: play videos in the gallery + lightbox
**Why:** render `<video controls>` for video items; keep `<img>` for photos.

### Steps
1. **DO NOT create a new detector — one already exists.** `EvidenceGallery.tsx` (~line 24) has a
   local `isVideo`:
   ```ts
   function isVideo(m: MediaItem): boolean {
     return /\.(mp4|mov|webm)$/i.test(m.filename ?? "");
   }
   ```
   **(a)** Extend it to also honor `capture_type` (belt-and-suspenders for any item whose filename
   is missing), and **(b)** `export` it so the lightbox can import the exact same function:
   ```ts
   export function isVideo(m: { capture_type?: string | null; filename?: string | null }): boolean {
     return /\.(mp4|mov|webm)$/i.test(m.filename ?? "") || !!m.capture_type?.endsWith("_video");
   }
   ```
   Do not widen the signature beyond what callers pass; `MediaItem` already has both fields, so
   existing call sites keep type-checking.
2. `EvidenceLightbox.tsx` (the full-size view): **import** `isVideo` from `EvidenceGallery.tsx`
   (do NOT copy it). Where it renders `<img src={url} …>` (~line 68), branch:
   if `isVideo(item)` → `<video src={url} controls playsInline style={{maxWidth:"100%"}} />`,
   else the existing `<img>`. Keep the same `fetchMediaUrl(item.operation_id)` → object-URL flow
   (it already works for any bytes).
3. `EvidenceGallery.tsx` (the thumbnail, ~line 170): same branch — for a video render
   `<video src={url} muted playsInline preload="metadata" />` (shows first frame as a thumb; no
   autoplay), else the existing `<img>`.
   ⚠️ **`<video>` does NOT fire `onLoad`.** The current `<img>` sets the `loaded` CSS class via
   `onLoad={() => setLoaded(true)}`. If you copy that onto `<video>`, `loaded` never turns true and
   the thumbnail stays invisible (opacity/reveal styles). Use **`onLoadedData={() => setLoaded(true)}`**
   on the `<video>` branch. Keep the existing `failed`/fallback states.
4. **Tests** (`EvidenceGallery.test.tsx` + `EvidenceLightbox.test.tsx`, extend — mock
   `fetchMediaUrl` as the existing test does): a `filename: "x.mp4"` (or `capture_type:
   "quenching_video"`) item renders a `<video>` element; a `filename: "x.jpg"` / `"batch_photo"`
   item renders an `<img>`. Also assert the video thumbnail becomes visible after firing
   `onLoadedData` (fireEvent.loadedData on the `<video>`), so the `onLoad`→`onLoadedData` trap is
   regression-covered.
5. **CHECKPOINT:** `npm test -- --run && npx tsc --noEmit && npm run build` all green.
**COMMIT:** `feat(portal): play video evidence (<video>) in gallery + lightbox`

---

## PART PV-3 — Backend: expose the temperature series on batch-detail
**Why:** the portal can't chart what the API doesn't send.

### Steps
1. In `backend/portal/routes.py::batch_detail`, after building `media`, load the batch's telemetry:
   ```python
   tel_row = (await session.execute(
       select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == buid)
   )).scalar_one_or_none()
   telemetry = None
   if tel_row is not None:
       p = await _safe_json_async(tel_row.payload_json, context=f"telemetry {buid}")
       if isinstance(p, dict):
           readings = p.get("temperature_readings")
           telemetry = {
               "temperature_readings": readings if isinstance(readings, list) else [],
               "min_temp": p.get("min_temp"),
               "max_temp": p.get("max_temp"),
               "burn_start_timestamp": p.get("burn_start_timestamp"),
               "burn_end_timestamp": p.get("burn_end_timestamp"),
           }
   ```
   Add `"telemetry": telemetry` to the returned dict.
   ⚠️ **Use `_safe_json_async`, NOT `_safe_json`** — import it: `from jsonsafe import _safe_json_async`.
   A real burn's `temperature_readings` can be ~100k floats; parsing that with the sync `_safe_json`
   on the event loop stalls every other request. `_safe_json_async` (same defensive contract, returns
   the parsed object or `None`, never raises) offloads big payloads to a thread — it exists for
   exactly this payload. `batch_detail` is already an `async def`, so `await` is fine.
   Note: `min_temp`/`max_temp` may be absent from the payload (they are today) → they come back `null`;
   that is fine, the chart derives its own lo/hi from `temperature_readings`.
2. `portal/src/api.ts`: extend the `BatchDetail` interface with
   `telemetry: { temperature_readings: number[]; min_temp: number | null; max_temp: number | null;
   burn_start_timestamp: string | null; burn_end_timestamp: string | null } | null;`
3. **Test** (extend the batch-detail backend test, or `test_portal_read.py`): a batch with a
   telemetry row returns `telemetry.temperature_readings` non-empty; a batch with none returns
   `telemetry == null`. Malformed `payload_json` → `telemetry` is null or has `[]` (never 500).
4. **CHECKPOINT:** backend suite green; `npx tsc --noEmit` green (interface change compiles).
**COMMIT:** `feat(backend): expose burn temperature series on batch-detail`

---

## PART PV-4 — Portal: temperature chart (inline SVG) + post-burn weight stat
**Why:** the actual visual the client sees.

### Steps
1. New component `portal/src/components/TemperatureChart/TemperatureChart.tsx` — **inline SVG, no
   dependency.** Props: `readings: number[]`, `minTemp: number | null`, `maxTemp: number | null`.
   - Empty/absent readings → render an empty state ("No thermocouple telemetry for this batch").
     Never crash on `[]` or `undefined`.
   - Otherwise draw a `viewBox="0 0 600 200"` SVG with a single `<polyline>`:
     `x_i = (i/(n-1))*600` (if `n===1`, render a single `<circle>` dot instead of a line);
     `y_i = 200 - ((t_i - lo)/(hi - lo))*200` where `lo = min(readings)`, `hi = max(readings)`,
     with a guard so `hi===lo` doesn't divide by zero (fall back to a flat mid-line).
   - Add simple min/max axis labels (text) — enough to read the curve. Keep it small; theme it with
     the existing CSS variables (e.g. stroke `var(--accent…)`), don't hardcode brand colors.
2. In `portal/src/pages/BatchDetail.tsx`, render a "Burn telemetry" panel:
   - `<TemperatureChart readings={d.telemetry?.temperature_readings ?? []} minTemp={d.telemetry?.min_temp ?? null} maxTemp={d.telemetry?.max_temp ?? null} />`
   - Next to/under it, a **stat** (reuse the existing `StatTile`/`MetricBlock` component if present):
     `Post-burn yield: {d.batch.wet_yield_kg} kg`, and `Min/Max temp` from telemetry.
   - **Add this exact code comment** so no one "fixes" it into a fake curve later:
     `{/* Weight is a single post-burn measurement, not a time series — shown as a stat, not a curve. A weight-vs-time curve would require app-side series capture (out of scope). */}`
3. **Tests** (`TemperatureChart.test.tsx`, new; mirror an existing component test): renders a
   `<polyline>` (or path) when given ≥2 readings; renders the empty state for `[]`; does not crash
   for a single reading.
4. **CHECKPOINT:** `npm test -- --run && npx tsc --noEmit && npm run build` all green.
**COMMIT:** `feat(portal): burn temperature chart + post-burn yield stat on batch detail`

---

## FINAL — regression + honest note
```
cd backend && python -m pytest -q
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```
All green before you report done. Then re-seed the demo (`seed_demo.py`) if you want the HERO batch
to show the chart + (once the app captures one) a playable video.

**Report back, explicitly:** that video **playback** is now wired (PV-1/PV-2); that the temperature
curve is **real data**; and that the weight is shown as a **single post-burn value, not a
fabricated curve** — and that a true weight-over-time curve remains a separate app-side feature not
built here.

## Definition of Done
- [ ] A video evidence item plays in the portal gallery + lightbox (`<video controls>`); photos
      still render as `<img>`. Backend serves `video/mp4`/`image/jpeg`.
- [ ] Batch detail shows a real thermocouple temperature curve (inline SVG) from
      `temperature_readings`, with a graceful empty state.
- [ ] Post-burn yield weight shown as a labeled value — **no fabricated weight curve.**
- [ ] No new dependency, no migration, no schema change. Backend + portal suites + tsc + build all
      green before and after. One commit per PART.
