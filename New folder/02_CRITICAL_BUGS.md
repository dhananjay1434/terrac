# 02 — Critical Functional Bugs (broken *today*)

These are not opinions about quality — these are defects that mean the
advertised flow does not work. Ordered by blast radius.

---

## 🔴 BUG-1 — The main measurement payload is rejected by the server (HTTP 422, always)
**Files:** `lib/data/local/app_database.dart:276-300` (biomass payload),
`lib/services/sync_queue_manager.dart:212-219` (endpoint routing),
`backend/server.py:69-119` (`BatchPayload`, `extra="forbid"`)

The biggest "feature" — capturing biomass sourcing and syncing it — is dead on
arrival:

1. The client builds the biomass outbox payload with these keys:
   `sourcing_uuid, batch_uuid, feedstock_species, harvest_timestamp,
   moisture_percent, moisture_compliant, photo_path, sha256_hash, latitude,
   longitude, mock_location_enabled, harvest_uptime_seconds, azimuth, pitch,
   roll` (`app_database.dart:276-293`).
2. `targetTable == 'biomass_sourcing'` is **not** in the endpoint map
   (`sync_queue_manager.dart:213-219`), so it falls through to the default
   endpoint `batches`.
3. `BatchPayload` declares `model_config = ConfigDict(extra="forbid", …)`
   (`server.py:119`). The payload's extra fields —
   `sourcing_uuid, moisture_compliant, mock_location_enabled, azimuth, pitch,
   roll` — are **forbidden**, so Pydantic returns **422 every time**.
4. Even if extras were allowed, `sha256_hash` is `Field(..., min_length=64)`
   (required, non-null). The client sends `sha256_hash: null` whenever no photo
   was attached → still 422.

**Consequence:** No biomass batch ever reaches the server. The "offline-first,
two-phase, idempotent sync" engine retries a request that can never succeed,
increments `retryCount`, and after 11 tries marks it `FAILED_PERMANENTLY`
(`sync_queue_manager.dart:168-177`) — i.e. **silent permanent data loss** of the
core MRV record.

**Fix direction:** Define an explicit contract per `targetTable`. Either route
biomass to a dedicated endpoint/schema, or align field names and relax/whitelist
the schema. Add a contract test that POSTs the *actual* client payload.

---

## 🔴 BUG-2 — Four core endpoints are empty stubs that persist nothing
**File:** `backend/server.py:489-515`

```python
@app.post("/api/v1/telemetry") ... return {"status": "success", "duplicate": False}
@app.post("/api/v1/yield")     ... return {"status": "success", "duplicate": False}
@app.post("/api/v1/metadata")  ... return {"status": "success", "duplicate": False}
@app.post("/api/v1/application")... return {"status": "success", "duplicate": False}
```

They accept `payload: dict` (no validation), check only that `batch_uuid` is a
string, and **return success without writing anything** — despite the fact that
matching tables exist (`PyrolysisTelemetry`, `YieldMetrics`,
`EndUseApplication` in `models.py:68-102`).

**Consequence:** Pyrolysis telemetry, yield, end-use, and system-metadata are
**accepted and discarded**. The client marks them `SYNCED` and **deletes the
local evidence file** (`sync_queue_manager.dart:407`). So the data is gone on
both ends. This is the worst kind of bug: it looks like success.

**Fix direction:** Implement real persistence with validated Pydantic schemas
and idempotency, or return `501` until implemented (so the client keeps data).

---

## 🔴 BUG-3 — `system_metadata` (the batch's identity record) is routed to a stub
**Files:** `lib/data/local/app_database.dart:172-204`, `sync_queue_manager.dart:219`,
`backend/server.py:503-508`

`insertSystemMetadataWithOutbox` is the very first thing written for a batch
(artisan id, device MAC, build). It routes to `metadata` →
`/api/v1/metadata`, which is the stub from BUG-2. So a batch is never actually
registered server-side; later media/anchoring logic that assumes a batch exists
has nothing to bind to.

---

## 🔴 BUG-4 — Device registration is hardcoded to the emulator and will never run in production
**File:** `lib/services/crypto_signer.dart:61-81`

`registerDevice()` is called unconditionally at startup (`warmUp()`), but posts
to `http://10.0.2.2:8000/api/v1/register` — the Android-emulator loopback alias,
plaintext, fixed port 8000. On a real device this resolves to nothing →
registration fails (silently caught at `:78-80`). The device key is therefore
**never registered**, so every subsequent signed request hits SEC-2's global
fallback or fails HMAC. The sync layer's base URL is env-driven; registration's
is not. They are simply inconsistent.

**Fix direction:** Registration must use the same env-configured base URL/HTTPS
as sync, and must be retried/awaited as part of a real enrollment flow.

---

## 🟠 BUG-5 — Riverpod misuse in SyncQueueManager constructor
**File:** `lib/services/sync_queue_manager.dart:63-64`

```dart
final db = ref.read(appDatabaseProvider);          // returns AsyncValue<AppDatabase>
_dbSubscription = db.tableUpdates(...).listen(...);  // tableUpdates is on AppDatabase
```

`appDatabaseProvider` is a `FutureProvider.autoDispose<AppDatabase>`
(`database_provider.dart:10`), so `ref.read(...)` yields an
`AsyncValue<AppDatabase>`, which has no `tableUpdates`. Elsewhere the code
correctly uses `await ref.read(appDatabaseProvider.future)` (`:153`). This
constructor path is a type error / runtime failure depending on build state and
should be fixed and covered by a test. (The committed `build/` predates the
current source, so "it compiled once" is not evidence it compiles now.)

---

## 🟠 BUG-6 — `appDatabaseProvider` mixes `autoDispose` + `keepAlive` + `onDispose(close)`
**File:** `lib/data/local/database_provider.dart:10-15`

`autoDispose` is declared, then immediately negated by `ref.keepAlive()`, while
also registering `ref.onDispose(db.close)`. The net behavior is "never dispose,
but pretend to" — the `db.close` hook effectively never runs, and the comment
about mitigating a `secureWipe` race is wishful. Either make it a plain
`Provider`/`FutureProvider` with an explicit lifecycle, or genuinely allow
disposal. As written it is self-contradictory and the wipe race it claims to fix
is not actually addressed.

---

## 🟠 BUG-7 — Media↔batch anchoring by SHA-256 can crash and mis-bind
**File:** `backend/server.py:319-322, 460-462`

Anchoring matches `MediaFile.sha256_hash == Batch.sha256_hash` and uses
`scalar_one_or_none()`. Two media rows (or two batches) sharing the same photo
hash → **`MultipleResultsFound` → HTTP 500**. Also, `sha256_hash` is not unique
on either table, so the same photo reused across batches anchors to the wrong
one. Anchoring should be by an explicit `batch_uuid` reference the client
supplies, not by content-hash coincidence.

---

## 🟠 BUG-8 — Race-recovery path can 500 on the wrong unique constraint
**File:** `backend/server.py:293-305`

After an `IntegrityError`, the handler re-selects by `batch_uuid` and calls
`scalar_one()`. But the table has **two** unique constraints (`batch_uuid` *and*
`operation_id`, `models.py:20-21`). If the integrity violation was on
`operation_id` (same idempotency key, different `batch_uuid`), the
`batch_uuid` lookup returns nothing → `scalar_one()` raises `NoResultFound` →
unhandled 500 instead of a clean 409.

---

## 🟡 BUG-9 — Media upload requires a device id it declares optional, with a confusing error
**File:** `backend/server.py:352, 421-431`

`x_device_id` is `Header(None, ...)` (optional), but `_safe_device(x_device_id)`
regex-matches `s or ""`; `None`/empty fails and raises `400 invalid_device_id`.
So an upload without a device id always fails with a misleading message, and the
optional typing lies about the contract.

---

## 🟡 BUG-10 — `FAILED_PERMANENTLY` after 11 retries loses legitimate offline data
**File:** `lib/services/sync_queue_manager.dart:168-177`

`retryCount` increments on *every* failure, including transient ones (and the
guaranteed-failing BUG-1 case). With exponential backoff capped at `1<<10` and a
hard cutoff at 11, a row that is failing for a recoverable reason (or simply long
offline with intermittent wakeups) is permanently abandoned and never surfaced
to the user. For a tool whose whole point is rural offline resilience, silent
permanent failure is the wrong default — failures must be visible and
recoverable.
