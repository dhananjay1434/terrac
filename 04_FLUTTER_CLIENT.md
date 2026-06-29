# 04 — Flutter Client Architecture

~16.9k LOC of Dart (of which 7.8k is generated `app_database.g.dart`). The app
is genuinely ambitious: Riverpod state, Drift + SQLCipher encryption at rest,
transactional outbox sync, secure camera capture with EXIF + sensor telemetry,
BLE thermocouple/scale integration, RASP. There is real engineering here. It is
also over-built relative to a backend that can accept its data, and several
core paths are broken or self-contradictory.

---

## Architecture overview

```
UI screens (lib/ui/screens/*)            ← 8 screens, some 500-700 LOC
   │  Riverpod notifiers (lib/providers/*)
   ▼
AppDatabase (Drift + SQLCipher)          ← encrypted local source of truth
   │  Transactional Outbox (SyncOutbox table)
   ▼
SyncQueueManager                          ← polls + reacts to connectivity/db
   │  CryptoSigner (HMAC), TLS pinning
   ▼
FastAPI backend                           ← (mostly stubs / rejects payloads)
```

The **Transactional Outbox pattern** (write domain row + outbox row in one
transaction, then sync) is the right architecture for offline-first. The
encryption-at-rest implementation (SQLCipher key in Keystore/Keychain, parameter
-quoted `PRAGMA key`, fail-fast decrypt probe) is a real strength
(`app_database.dart:372-409`, `passphrase_resolver.dart`).

---

## 🔴 Client issues that break flows
(See `02_CRITICAL_BUGS.md` for full detail — summarized here.)

- **BUG-1**: biomass payload shape ≠ server schema → 422 forever.
- **BUG-4**: `registerDevice()` hardcoded to emulator `http://10.0.2.2:8000`.
- **BUG-5**: `ref.read(appDatabaseProvider)` used where `.future` is required
  (`sync_queue_manager.dart:63`).
- **BUG-6**: `appDatabaseProvider` `autoDispose`+`keepAlive` contradiction.

---

## 🟠 Sync engine concerns (`sync_queue_manager.dart`)

| # | Issue | Why it matters |
|---|-------|----------------|
| 🟠 | `_stampMediaSynced` is reached "unconditionally" if no throw (`:320-323`) — the success/no-op/error branches are entangled with comments instead of explicit control flow | Easy to regress into marking unsynced rows as synced and **deleting evidence** (`:407`) |
| 🟠 | Permanent failure after 11 retries with no user-visible surface (BUG-10) | Silent data loss in exactly the rural scenario the app targets |
| 🟠 | A single shared `_isSyncing` bool guards re-entrancy; `kickSync`, periodic timer, connectivity, and db-update streams can all fire — fine, but there's no jitter and every wake re-scans all PENDING rows serially | Thundering-herd on reconnect; long loops block subsequent kicks |
| 🟡 | `SyncConfig(apiBase: '')` default + "fails fast in tests" — but production relies on a `--dart-define` being present; a missing flag silently no-ops sync (`:142-148`) rather than failing at boot | Misconfigured release ships a no-op sync |
| 🟡 | `hmacSignature` is stored on the outbox row (`tables.dart:170`) and a *separate* `signRequest` canonical signature is computed at send time; two signing schemes coexist (`signPayload` vs `signRequest`) | Confusing; the stored payload HMAC is never sent/verified |

---

## 🟠 Secure capture (`secure_capture_service.dart`)
- Solid: re-encode in isolate, sandbox dir, hash *after* EXIF write, cleanup
  manifest for failed temp deletes, classified permission errors.
- 🟠 **EXIF is self-written by the app** (`:216-229`) — GPS/timestamp in EXIF is
  not independent evidence; it's whatever the app chose to write. Presented as
  "indelible digital fingerprint," but the hash only proves the file didn't
  change *after* the app wrote it, not that the contents are truthful.
- 🟡 Orientation/azimuth telemetry has a 500 ms timeout and returns `{}` on
  failure (`:308-332`); downstream treats missing telemetry as acceptable, so
  the "Sybil defense" sensor data is best-effort and easily absent.

---

## 🟠 Location service (`location_service.dart`)
- `DemoLocationService` **fabricates** Delhi coordinates (28.6139, 77.2090) with
  `isMocked: true` when GPS is unavailable (`:58-72`). Gated out of release via
  the provider (`:79-84`) and CI grep (`scripts/ci_grep_demo.sh`) — acceptable,
  but a fabricated-GPS path in a "truth machine" codebase is a liability that
  one missed guard turns into fraud.
- `pos.isMocked && kReleaseMode` (`:36`) means mock-GPS is **only** blocked in
  release; debug/profile/sideload builds accept mock locations.

---

## 🟡 App composition / lifecycle (`main.dart`)
- Creates a bare `ProviderContainer()` and reads `deviceIntegrityServiceProvider`
  imperatively before `runApp` (`:48-49`), then hands it to
  `UncontrolledProviderScope`. Works, but mixes manual container management with
  declarative scope; easy to leak or double-init providers.
- Device-integrity result only flips a flag; nothing in `main` blocks the app on
  compromise (enforcement gap, see SEC-8).
- `CryptoSigner.warmUp()` (which calls the broken `registerDevice`) is awaited at
  cold start before `runApp`; a slow/hanging network call here delays first
  paint.

---

## 🟡 Misc client smells
- `getBatchTelemetryUnsafe` (`app_database.dart:305-310`) — a "test-only"
  unsafe raw query shipped in production code.
- `schemaVersion = 15` with `onUpgrade` branches missing for some versions
  (no `from < 5/13/14`); the chain works only because those bumps had no DDL,
  but it's fragile and undocumented.
- Heavy reliance on `SharedPreferences` for security-relevant state
  (`artisan_id`, `device_mac`, `harvest_timestamp`/uptime in
  `lantana_sourcing_notifier.dart`) — unencrypted, user-readable on rooted
  devices, and the clock-spoof "uptime" defense reads `/proc/uptime` which is
  trivially unavailable on iOS (returns null → defense absent there).

---

## What's actually good here
- Encryption-at-rest design and key handling.
- Transactional outbox pattern.
- TLS pinning that fails closed in release.
- Thoughtful, classified error UX in capture/permissions.
- The `devBypass` 72h-lock override is correctly `assert()`-stripped from
  release builds (`lantana_sourcing_notifier.dart:198-207`) — good discipline.
