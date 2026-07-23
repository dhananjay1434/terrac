# Capture-Integrity Gate Rollout Runbook

**Status: both gates ship OFF today, on purpose.** The blur gate and geofence-warning gate
(V8 Part 4 (E)) exist, are wired into the capture pipeline, and are now proven correct on
their ON path (PR-7 — see `shouldRejectForBlur`/`geofenceWarningFor` in
`lib/services/secure_capture_service.dart` and their tests). What has **not** happened yet is
field calibration — the blur threshold and geofence buffer are reasonable starting guesses,
not numbers tuned against real kiln-site photos and real GPS noise. Flipping either default
to `true` before that calibration risks blocking or warning on *legitimate* captures, which
is worse than shipping the gate dormant.

This document is the calibration procedure and the rollout order for turning them on for
real, once someone actually runs it.

---

## The two gates

| Gate | Flag | Default | What it does |
|---|---|---|---|
| Blur rejection | `DMRV_BLUR_GATE_ENFORCED` | `false` | Rejects a photo capture outright (throws, no file ever written) when `computeBlurVariance(frame) < kBlurVarianceThreshold` (currently `60.0`). |
| Geofence warning | `DMRV_GEOFENCE_CAPTURE` | `false` | Sets `SecureCaptureResult.geofenceWarning = true` when the capture's GPS fix falls outside the batch's registered parcel boundary + a buffer (currently `10.0` meters). **Never blocks** — it's a review signal, not a rejection. |

Both are compile-time `bool.fromEnvironment` consts (same pattern as `DMRV_DEMO_MODE`
elsewhere in this codebase) — they cannot be toggled at runtime, only at build time via
`--dart-define`.

---

## Step 1 — Collect real field data (do this first, before touching any threshold)

**Blur:**
1. Build the app with both gates OFF (today's default — no `--dart-define` needed).
2. Have field operators capture a normal week of evidence photos across the conditions that
   actually occur: bright sun, dusk, handheld motion, smoke haze near the kiln, low-end
   device cameras if the fleet is mixed hardware.
3. Every `SecureCaptureResult` already carries `blurVariance` — log it (or temporarily
   surface it in a debug overlay) alongside whether a human reviewer judged that specific
   photo "usable evidence" or "too blurry to read." You need this labeled pairing
   (variance number ↔ human judgment) to calibrate against, not variance numbers alone.

**Geofence:**
1. With the gate still OFF, capture evidence at real parcel boundaries — specifically
   operators standing *near* the registered edge, not just the center of a large parcel.
2. Every `SecureCaptureResult` carries the raw GPS fix; compare it against the parcel's
   stored `boundary_geojson` server-side (the backend's own corroboration buffer in
   `geometry.py` is the reference — this on-device buffer is deliberately set to match it,
   see `kGeofenceBufferMeters`'s doc comment).
3. Look for the actual GPS noise floor in the field (urban/rural signal quality, device GPS
   chipset variance) — a buffer smaller than the real noise floor will warn on every
   legitimate capture at a parcel edge.

**How much data is enough?** There's no universal number; the point is a labeled sample big
enough to place a threshold with confidence, not a single afternoon's photos. If the fleet
spans meaningfully different conditions (multiple device models, multiple terrains), sample
across that spread, not just one facility.

## Step 2 — Tune the constants

- `SecureCaptureService.kBlurVarianceThreshold` (currently `60.0`) — pick the value that best
  separates "reviewer said usable" from "reviewer said too blurry" in your labeled sample.
  Err toward a lower threshold (fewer false rejections) the first time you enable this in
  production; you can raise it later once you trust the false-rejection rate is low.
- `SecureCaptureService.kGeofenceBufferMeters` (currently `10.0`) — pick a buffer at least as
  large as the observed GPS noise floor at parcel edges. Widening it is always safe (fewer
  false warnings); narrowing it below the real noise floor produces spurious warnings on
  correct captures.

Change these as a normal code edit + PR — they are not runtime-configurable, so a threshold
change requires a new build.

## Step 3 — OFF → canary → ON rollout

Per the standing rollout discipline (see EXECUTION_MASTER_PLAN §0.7.5 if present, or the
project's general "flag-gated, staged" convention):

1. **OFF (today).** No dart-define set. Confirm this is still the default build.
2. **Canary.** Build a small subset of devices (one facility, or a handful of operators) with
   the calibrated thresholds and the enforcement flag(s) ON:
   ```
   flutter build apk --dart-define=DMRV_BLUR_GATE_ENFORCED=true
   flutter build apk --dart-define=DMRV_GEOFENCE_CAPTURE=true
   ```
   (Combine both in one build if enabling together: `--dart-define=DMRV_BLUR_GATE_ENFORCED=true --dart-define=DMRV_GEOFENCE_CAPTURE=true`.)
   Run the canary for long enough to observe the false-rejection / false-warning rate across
   real field conditions — not just a day. Watch specifically for: operators reporting
   repeated blur rejections on genuinely fine photos, or geofence warnings at legitimate
   parcel-edge captures.
3. **Full rollout.** Only after the canary shows an acceptably low false-positive rate, flip
   the flag(s) on for the full fleet's release build. Consider enabling the two gates
   independently (blur first, geofence second, or vice versa) rather than simultaneously, so
   a problem is attributable to one gate, not both at once.

**Roll back** by simply omitting the `--dart-define` (or setting it `false`) in the next
build — there is no server-side state to unwind; these are client-only capture-time checks.

## What this Part did NOT do

- Did not flip either default to `true` — both gates ship OFF, exactly as before.
- Did not invent calibration numbers — `kBlurVarianceThreshold`/`kGeofenceBufferMeters` are
  unchanged; Step 1/2 above is real work someone still has to run against real field data.
- Did not build the labeled-sample collection tooling (a debug overlay, a log-shipping path)
  — Step 1 describes what's needed; building it is a separate, smaller Part if desired.
