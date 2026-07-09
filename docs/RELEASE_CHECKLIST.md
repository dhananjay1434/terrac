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

## Release signing (P0.6)

- Release builds are signed via `android/key.properties` (gitignored). CI has no
  keystore and falls back to debug signing for the compile-smoke only.
- **The release keystore (`*.jks`) and its passwords MUST be backed up off-machine**
  (password manager + one offline copy). Losing it = losing the Play update
  identity permanently. See `android/key.properties.example`.

## On-device release validation (P0.7 — pending a physical Android device)

_To be filled by P0.7: scripted PASS/FAIL walk of a signed `--release` build on a
real device (launch, FLAG_SECURE, camera+EXIF, BLE, full batch sync, kill/resume,
offline→reconnect, background sync, permission dialogs, 16 KB page-size)._

## Play publishing (P4.9 — pending)

_To be filled by P4.9: tag-driven appbundle build, symbol upload to Sentry,
upload to the Play internal track; promotion internal→closed→production is always
a human action._
