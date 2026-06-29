# Prompt 3 — Camera Sandbox, Hashing & DB Wiring

## What was added / changed

| Concern | File | Status |
| --- | --- | --- |
| Batch session state (Gap 5.3) | `lib/providers/batch_session_notifier.dart` | **new** |
| Anti-fraud capture pipeline (sandbox + EXIF + SHA-256) | `lib/services/secure_capture_service.dart` | **new** |
| Full-screen secure camera (Task 2) | `lib/ui/screens/secure_camera_screen.dart` | **new** |
| DB writer for BiomassSourcing + outbox | `lib/data/local/app_database.dart` → `insertBiomassSourcingWithOutbox()` | extended |
| Schema v2: `photoPath`, `sha256Hash`, `latitude`, `longitude` | `lib/data/local/tables.dart` + migration in `app_database.dart` | extended |
| Moisture screen wired to camera + DB (Gap 5.1) | `lib/ui/screens/moisture_verification_screen.dart` | rewritten |
| Moisture state holds evidence + `persisted` flag | `lib/providers/moisture_gate_notifier.dart` | rewritten |
| Dashboard `START NEW BATCH` mints UUID v4 | `lib/ui/screens/dashboard_screen.dart` | rewritten |
| Field-debug screen | `lib/ui/screens/camera_debug_view.dart` | **new** |
| Android permissions | `android/app/src/main/AndroidManifest.xml` | extended |
| iOS usage strings | `ios/Runner/Info.plist` | extended |
| Dependencies | `pubspec.yaml` | extended |

## One-time setup on your dev box

```bash
cd flutter_dmrv
flutter pub get
# Regenerate Drift codegen — REQUIRED because tables.dart changed.
dart run build_runner build --delete-conflicting-outputs
```

If Android complains about minSdk for the `camera` plugin, set
`flutter.minSdkVersion = 21` in `android/app/build.gradle.kts` (most setups
already are).

## Routing into the CameraDebugView

There are **two** routes — pick whichever is faster on your device.

### 1) Long-press easter egg (recommended for field testing)
Long-press the **SYNC BUFFER** counter on the Dashboard for ~1.2 seconds. This
pushes `CameraDebugView` onto the navigation stack without modifying any
release-only UI.

### 2) Imperative route (e.g. wire to a developer menu)
```dart
Navigator.of(context).push(
  MaterialPageRoute(builder: (_) => const CameraDebugView()),
);
```

## Running on a physical Android device

```bash
flutter devices                    # confirm device is listed
flutter run -d <device-id>         # debug build, hot reload enabled
```

When you tap **RUN CAPTURE PIPELINE**:

1. The notifier auto-starts a batch (Task 1) if none is active.
2. Full-screen `SecureCameraScreen` opens at `ResolutionPreset.medium`.
3. Pressing the shutter triggers `SecureCaptureService.capture()` which:
   * writes the JPEG (q=70) to `getApplicationSupportDirectory()/evidence/<uuid>.jpg`
   * fetches a GPS fix
   * stamps EXIF `GPSLatitude` / `GPSLongitude` / `DateTimeOriginal`
   * SHA-256-hashes the FINAL on-disk artifact
4. The view persists a `BiomassSourcing` row + matching `SyncOutbox` event via
   the atomic `AppDatabase.insertBiomassSourcingWithOutbox()` transaction.
5. The dashboard's `pendingOutboxCountProvider` stream increments by **+1**
   instantly (it watches the same outbox table).
6. A single `debugPrint` block is emitted to `adb logcat` AND rendered on the
   debug screen, containing:
   * The active **batchUuid**
   * The **sandboxed internal file path**
   * The parsed **EXIF DateTimeOriginal / GPSLatitude / GPSLongitude**
   * The calculated **SHA-256**
   * A confirmation that `insertWithOutbox` succeeded

Capture the log with:
```bash
adb logcat -s flutter:V | grep CameraDebugView
```

## Field-flow verification (normal user path)

1. Dashboard → tap **START NEW BATCH** → batch badge in the top-right populates.
2. Sourcing screen → use the `-73h TEST` button to satisfy the 72h lock.
3. Tap **PROCEED TO MOISTURE CHECK**.
4. Enter a compliant reading (e.g. `12.5`).
5. Tap **CAPTURE METER PHOTO** → secure camera launches.
6. Press the amber shutter → camera closes, the photo block shows the
   `sha256` / GPS / sandbox path, and `outbox: COMMITTED` lights up.
7. **`INITIATE PYROLYSIS`** button renders (gated on `compliant && photoCaptured && persisted`).
8. Back on the dashboard, **OFFLINE BUFFER** count is `01` and the
   `INSERT // biomass_sourcing` row appears in the OUTBOX strip.
