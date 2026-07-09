# RELEASE CHECKLIST

The repeatable, scripted steps that must pass before any dMRV release. Sections
are added as the release engineering tasks (P0.6–P0.8, P4.9) land.

## Dependency policy — "lock is law" (P0.10)

- **CI never resolves newer than the lockfile.** The Flutter CI runs
  `flutter pub get --enforce-lockfile`; the backend CI runs `python -m pip check`
  after installing the fully `==`-pinned `backend/requirements.txt`.
- **Before cutting a release branch:** run `flutter pub outdated` and review.
  Any dependency upgrade is its **own commit** with G1–G4 green — never bundled
  into a feature commit, never an unreviewed float.
- `pubspec.lock` and `backend/requirements.txt` are committed and authoritative.
  A bump to either is a deliberate, reviewed change.

## Release signing (P0.6) — DONE, verified

- Release builds are signed via `android/key.properties` (gitignored). CI has no
  keystore and falls back to debug signing for the compile-smoke only.
- Keystore: PKCS12, RSA-4096, alias `dmrv`, validity ~27 yrs. Generated
  2026-07-10, stored OUTSIDE the repo at `C:\Users\bit\dmrv-keystore\dmrv-release.jks`.
  NOTE: keytool makes PKCS12 by default → the key password EQUALS the store
  password (a distinct `-keypass` is silently ignored); `key.properties` reflects this.
- Signing cert fingerprints (PUBLIC — not secrets; needed for Play + freeRASP):
  - SHA-256: `c04e5392bb999748f57260eb5d2ea490b6c6209230dacb19e9e400c625f9d34b`
  - SHA-1:   `6ea5ccc67a6d097ff25d74196c931d47ff348ae7`
  - `TALSEC_SIGNING_CERT_HASH` derives from the SHA-256 (base64) — wire in P0.7/P4.1.
- Verified: `apksigner verify --print-certs app-release.apk` → `CN=dMRV …`, matching
  the keystore (not Android Debug).
- ⚠️ **BACKUP STILL REQUIRED (only human residual of P0.6):** the `.jks` exists on
  ONE machine. Copy it + its password (from `key.properties`) into a password
  manager and one offline location. Losing it = losing the Play update identity
  permanently. Until backed up, this is a single point of failure.

## 16 KB page-size compliance (P0.8 — DIAGNOSED, fix deferred)

Analyzed the arm64-v8a native libs in the release APK (ELF LOAD-segment
alignment). Result: **NOT yet 16 KB-compliant**, but cleanly isolated.

- COMPLIANT (≥0x4000): libflutter, libapp, libsqlcipher, libsentry(+android),
  libdartjni, and the CameraX jni libs — the Flutter engine and most plugins are fine.
- UNDER-ALIGNED (0x1000 / 4 KB) — all from the **freeRASP/Talsec** SDK:
  `libclib`, `libpbkdf2_native`, `libpolarssl`, `libsecurity`, `libtmlib`.

**Fix requires freeRASP 6.12.0 → 8.0.0 — a MAJOR bump** (16 KB support landed in
freeRASP 7.x+). Deferred deliberately because:
- It is API-breaking: `device_integrity_service.dart` uses `TalsecConfig`,
  `ThreatCallback`, `Talsec.instance.attachListener/start`, which changed across
  6→7→8; the bump needs a code migration.
- freeRASP is the anti-tamper/attestation SDK — the migration must be validated
  on a real device (ties into P0.7 and the P4.1 attestation flip).
- 16 KB is a **Play-submission** requirement (Android 15+), so it blocks nothing
  until P4.9; there is no value in rushing a breaking security-SDK migration now.

**Action when ready (own task, likely folded into P4.1):** bump freeRASP to 8.x,
migrate the ThreatCallback/config API, rebuild, re-run this alignment check
(all libs ≥0x4000), then re-run the on-device checklist.

## On-device release validation (P0.7 — pending a physical Android device)

_To be filled by P0.7: scripted PASS/FAIL walk of a signed `--release` build on a
real device (launch, FLAG_SECURE, camera+EXIF, BLE, full batch sync, kill/resume,
offline→reconnect, background sync, permission dialogs, 16 KB page-size)._

## Play publishing (P4.9 — pending)

_To be filled by P4.9: tag-driven appbundle build, symbol upload to Sentry,
upload to the Play internal track; promotion internal→closed→production is always
a human action._
