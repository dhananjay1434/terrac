# Prompt 5.1 — Yield, End-Use, SQLCipher, Env Config + GPS Recovery UX

## What was added / changed

### Task 1 — BLE Crane Scale (Yield)

| Concern | File | Status |
| --- | --- | --- |
| BLE Weight Scale transport (0x181D / 0x2A9D, SI flag + uint16 × 0.005) | `lib/services/ble_weight_scale_service.dart` | **new** |
| 5-reading circular buffer + <0.05 kg variance lock | `lib/providers/yield_scale_notifier.dart` | **new** |
| `YieldScaleScreen` (live load HUD, STABILIZED badge, LOCK + SAVE) | `lib/ui/screens/yield_scale_screen.dart` | **new** |
| `insertYieldMetricsWithOutbox()` atomic writer | `lib/data/local/yield_end_use_writers.dart` | **new** |
| Variance lock unit test | `test/scale_stabilization_test.dart` | **new** |

### Task 2 — Routing & End-Use Application

| Concern | File | Status |
| --- | --- | --- |
| INITIATE PYROLYSIS → `PyrolysisScreen` | `lib/ui/screens/moisture_verification_screen.dart` | patched |
| END BURN → `YieldScaleScreen` (pushReplacement) | `lib/ui/screens/pyrolysis_screen.dart` | patched |
| SAVE YIELD → `EndUseApplicationScreen` | `lib/ui/screens/yield_scale_screen.dart` | new |
| `EndUseApplicationScreen` (GPS, farmer photo, method dropdown, tonnage, transport km) | `lib/ui/screens/end_use_application_screen.dart` | **new** |
| `insertEndUseWithOutbox()` + `closeBatch()` | `lib/data/local/yield_end_use_writers.dart` | new |
| Schema v4 — `farmer_photo_path`, `farmer_photo_sha256` on `end_use_application` | `lib/data/local/tables.dart` + migration in `app_database.dart` | patched |

### Task 3 — AES-256 Encryption + Env-Driven API URL

| Concern | File | Status |
| --- | --- | --- |
| `sqlcipher_flutter_libs` + `sqlite3` deps | `pubspec.yaml` | patched |
| SQLCipher-backed `LazyDatabase` w/ 256-bit auto-generated passphrase persisted via `shared_preferences` | `lib/data/local/app_database.dart` | patched |
| `_apiBase` removed → `String.fromEnvironment('DMRV_API_BASE_URL')`; loop short-circuits when unset | `lib/services/sync_queue_manager.dart` | patched |

> ⚠️ The database file name changed from `dmrv.sqlite` to `dmrv_encrypted.sqlite`.
> Any rows you wrote during earlier phone tests live in the **old** plaintext
> file and will **not** be visible after this build. Uninstall + reinstall
> on your test phone (or `adb shell pm clear com.example.dmrv_app`) to start
> fresh — there is no migration path from plaintext → cipher.

---

## One-time rebuild on your dev box

```bash
cd dmrv_app
flutter pub get

# REQUIRED — Drift codegen for the new EndUseApplication columns + schema v4.
dart run build_runner build --delete-conflicting-outputs

# Run the variance-lock test (pure-Dart, no device needed).
flutter test test/scale_stabilization_test.dart
```

If Android complains about minSdk, set `minSdkVersion = 21` in
`android/app/build.gradle.kts` (SQLCipher requires NEON; 21+ is fine).

---

## Launch / build with the API endpoint

```bash
# Dev — points at your local FastAPI (still TBD).
flutter run -d <device-id> \
  --dart-define=DMRV_API_BASE_URL=http://10.0.2.2:8000/v1/sync

# Release APK — points at staging.
flutter build apk \
  --dart-define=DMRV_API_BASE_URL=https://staging.dmrv.example/v1/sync
```

If the flag is omitted, the sync loop logs a friendly notice and skips —
all your offline data is still safely buffered in the encrypted outbox.

---

## End-to-end field flow (now wired)

1. Dashboard → **START NEW BATCH**
2. Sourcing → `-73h TEST` → **PROCEED TO MOISTURE CHECK**
3. Moisture → enter `12.5` → **CAPTURE METER PHOTO** → **INITIATE PYROLYSIS**
4. Pyrolysis → **CONNECT ESP32 THERMOCOUPLE** → wait for samples → **END BURN**
5. Yield → **CONNECT CRANE SCALE** → wait for 5 readings within 50 g →
   **LOCK YIELD** → **SAVE YIELD**
6. End-Use → **CAPTURE APPLICATION GPS** + **CAPTURE FARMER ID / SELFIE** +
   pick **APPLICATION METHOD** + type **TONNAGE** + **TRANSPORT KM** →
   **COMMIT END-USE // CLOSE BATCH**
7. Lands back on Dashboard; **OFFLINE BUFFER** now shows 5 events
   (system_metadata + biomass_sourcing + pyrolysis_telemetry +
   yield_metrics + end_use_application).

---

## Tests

`test/scale_stabilization_test.dart` covers:

- 5 tight readings (Δ = 40 g) → `stableKg` == arithmetic mean.
- 5 wide readings (Δ = 200 g) → `stableKg` == `null`.
- Buffer < 5 → never locks even if variance is 0.
- Circular drop — wild readings followed by 5 tight ones still locks correctly.
- `confirm()` is a no-op pre-stabilization.
- `begin()` correctly wires the BLE stream into `pushReading`.
- The SIG byte parser (`parseWeightMeasurement`) under both SI and imperial flags.

---

## v5.1 — GPS Recovery UX

The Secure Camera no longer dead-ends on `SecureCaptureException: location
services`. The error pipeline is now classified (`CaptureErrorKind`) so the
in-screen error view renders the right recovery affordance:

| Kind | UI shows |
| --- | --- |
| `locationServiceOff` | red panel + **RETRY** + **OPEN LOCATION SETTINGS** |
| `locationPermissionPermanent` | red panel + **RETRY** + **OPEN APP SETTINGS** |
| `locationPermissionDenied` | red panel + **RETRY** (re-requests perm) |
| `cameraUnavailable` / `other` | red panel + **RETRY** |

GPS acquisition itself is now resilient too: the service tries
`getCurrentPosition` first (12 s timeout), then falls back to
`getLastKnownPosition()` if the device is slow / signal is weak. Only if
BOTH fail does the camera screen surface the recoverable error.
