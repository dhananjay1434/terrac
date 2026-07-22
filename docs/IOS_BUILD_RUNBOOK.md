# TerraCipher dMRV — iOS Build Runbook

**Why this exists.** Deferred item #8 (iOS build verification) cannot be completed on
this project's Windows development host — there is no Xcode, no CocoaPods, and
`flutter build ios` / `pod install` require macOS. This runbook is the exact,
reproducible procedure a macOS runner (human or CI) executes to close that gap. Until
someone runs this and confirms a launchable build, **the iOS line in the production
gate stays explicitly "unverified" — never marked done from a host that cannot build
it** (see `DEFERRED_WORK_EXECUTION_PLAN.md §0-DELTA.4`).

**What's already done (do NOT redo).** `ios/Runner/Info.plist` already declares every
permission string this app's plugins need:
- `NSCameraUsageDescription`
- `NSLocationWhenInUseUsageDescription`
- `NSPhotoLibraryAddUsageDescription`
- `NSBluetoothAlwaysUsageDescription`
- `NSBluetoothPeripheralUsageDescription`

`ios/Runner.xcodeproj/project.pbxproj` already sets `IPHONEOS_DEPLOYMENT_TARGET = 13.0`
across all three build configurations (Debug/Release/Profile). Do not re-add permission
strings or bump the deployment target without a reason — both were deliberately set
during earlier phases of this project.

**What is NOT done yet.** There is no `ios/Podfile` — it does not exist in this repo.
CocoaPods generates it on first `pod install`. This is normal and expected; it is not a
missing file to restore, it's a file to generate.

---

## Prerequisites (macOS runner)

| Tool | Minimum version | Check with |
|---|---|---|
| macOS | 13 (Ventura) or later — whatever Xcode's own minimum is at build time | `sw_vers` |
| Xcode | Whatever's current on the App Store; must support iOS 13.0 deployment target | `xcodebuild -version` |
| Xcode Command Line Tools | Matching the installed Xcode | `xcode-select -p` |
| Flutter SDK | 3.41.9 (stable channel) or newer — this repo's `pubspec.yaml` pins Dart SDK `^3.11.5` | `flutter --version` |
| CocoaPods | Latest (`gem install cocoapods` or `brew install cocoapods`) | `pod --version` |
| A valid Apple Developer signing identity/team | — | Xcode → Settings → Accounts |

## Step-by-step

```bash
# 1. From the repo root, fetch Dart/Flutter packages.
flutter pub get

# 2. Pre-cache the iOS engine artifacts (safe to re-run; no-ops if already cached).
flutter precache --ios

# 3. Generate the iOS Podfile + install native dependencies.
#    THIS is what creates ios/Podfile — do not hand-write one.
cd ios
pod install
cd ..

# 4. Open the WORKSPACE (never the .xcodeproj directly — CocoaPods requires
#    the .xcworkspace so its generated Pods project is included).
open ios/Runner.xcworkspace
```

In Xcode:

5. Select the `Runner` target → **Signing & Capabilities** → choose your team /
   provisioning profile. (This project's Android side uses `DMRV_PROJECT_ID`-style
   dart-defines for runtime config, not build-time signing — iOS code-signing is
   entirely an Xcode-side concern, unrelated to those.)
6. Select a simulator or a connected device as the run target.
7. Build and run (⌘R) for a first smoke pass, OR build a release archive from the CLI:

```bash
flutter build ios --release \
  --dart-define=DMRV_API_BASE_URL=<your backend URL> \
  --dart-define=SENTRY_DSN=<your Sentry DSN>            # required in release mode — see below
  # Optional, only if attestation/RASP is being exercised on this build:
  # --dart-define=TALSEC_SIGNING_CERT_HASH=<hash>
  # --dart-define=TALSEC_IOS_TEAM_ID=<team id>
```

**Do not omit `SENTRY_DSN` on a release build.** `lib/main.dart::validateReleaseConfig`
throws `StateError` at boot if `kReleaseMode` is true and the DSN is empty — this is an
intentional fail-closed guard (a release build must never ship blind to crash
reporting), not a bug to work around.

## Per-plugin smoke test (do all of these — a build succeeding is necessary, not sufficient)

Every one of these has an iOS-native side that CocoaPods must resolve and that only
actually proves itself on a device/simulator run, not at compile time:

| Plugin | What to verify on-device |
|---|---|
| `camera` (^0.11.0+2) | Full-screen camera preview opens; a photo capture completes and the resulting file exists in the app's sandboxed support directory (never Photos/Camera Roll). |
| `geolocator` (^13.0.1) | Location permission prompt appears; a GPS fix is acquired (or the demo-mode fallback, if built with `--dart-define=DMRV_DEMO_MODE=true` in a debug build only — this flag is refused outright in release, by design). |
| `mobile_scanner` (^7.4.0) | QR scan screen opens the camera and successfully decodes a test QR code (e.g. the enrollment or field-walk-link flows). iOS minimum is 12.0 — well under this project's 13.0 target, so no compatibility gap expected, but confirm the scan UI actually renders. |
| `flutter_reactive_ble` (^5.4.0) | Bluetooth permission prompt appears; the app can discover/connect to a BLE peripheral (weight scale / thermocouple flows). |
| `flutter_secure_storage` (^9.2.2) | App launches without a Keychain-access crash; enrollment/crypto-key flows that read/write secure storage succeed. |
| `sqlcipher_flutter_libs` (^0.6.4) | The encrypted local DB opens successfully (app boots past the splash screen into the dashboard/enrollment screen without a DB-open exception). |
| `native_exif` (^0.6.2) | A captured photo's EXIF GPS/timestamp tags read back correctly (exercised by the same capture flow as `camera` above). |
| `freerasp` (^6.1.1) | In a debug build, integrity checks should be a documented no-op (`device_integrity_service.dart` skips them outside release). In an actual release build, confirm it does NOT crash the app at launch — RASP misconfiguration is a known way to hard-lock legitimate installs (see this project's commit history for a prior Android-side incident of exactly this). |
| `permission_handler` (^11.3.1) | All the above permission prompts (camera, location, bluetooth) actually surface — a silent denial with no OS prompt indicates a missing Info.plist key (shouldn't happen here, but verify). |
| `sentry_flutter` (^8.2.0) | Force a test exception (or check Sentry's dashboard after a real one) and confirm it's captured — this is the release-mode fail-closed guard's whole point. |

## Known deltas / things this Windows-authored session could NOT verify

- **No `ios/Podfile` exists yet** — first `pod install` (step 3 above) generates it.
  If `pod install` fails, the error will be the first real signal of an actual iOS
  dependency conflict; do not attempt to hand-write a Podfile to route around it.
- **`mobile_scanner` iOS minimum (12.0) vs. this project's deployment target (13.0):**
  compatible on paper (target exceeds the plugin's floor), but never actually built/run
  on iOS by this session — confirm via the smoke test row above.
- **freerasp iOS-side configuration** (`TALSEC_IOS_TEAM_ID`, `TALSEC_SIGNING_CERT_HASH`)
  has never been exercised on iOS in this project — only Android's equivalent
  (`Config.AndroidConfig`) has field history. Treat the first iOS RASP-enabled build as
  genuinely new territory, not a known-good path.
- **No CI pipeline builds iOS today.** This runbook is written for a human running it
  manually; wiring it into CI (e.g. a macOS GitHub Actions runner) is future work, not
  covered here.

## Definition of Done (only a macOS runner can check these off)

- [ ] `pod install` completes without dependency resolution errors.
- [ ] `flutter build ios --release` (with the required dart-defines) completes.
- [ ] The app launches to the enrollment screen (fresh install) or dashboard (already
      enrolled) without a boot-time crash.
- [ ] Every row in the per-plugin smoke-test table above has been exercised and passes.
- [ ] Findings — especially any FAILURE — are appended to this file's "Known deltas"
      section and reported back, so the next runner (or this plan's iOS DoD line) isn't
      relying on stale, unverified assumptions.

Until every box above is checked by an actual macOS run, `DEFERRED_WORK_EXECUTION_PLAN.md
§7-DELTA`'s iOS line stays **"iOS build UNVERIFIED — needs macOS runner."**
