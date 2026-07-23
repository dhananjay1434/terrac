# Burn-Telemetry Resilience — Tier-1 Design Report

**Author's stance:** independent CTO/architect review. Scope: the three Tier-1 findings from the
cheap-Android thermal/durability audit, all of which converge on the **pyrolysis burn pipeline** —
the app's longest, least-interruptible, highest-value operation. Goal: solve them for the real
₹8-15k-phone field reality **without touching the cryptographic trust core** (device Ed25519
signing, SHA-256 evidence hashing, server-side corroboration, SQLCipher-at-rest).

---

## 0. The two insights that shape everything below

Before any fix, two architectural facts (verified in code) reframe the whole problem:

**Insight A — the signing boundary is at UPLOAD, not at capture.**
The burn's temperature array is Ed25519-signed *once*, when the sync-outbox row is created at
`endBurn` (`pyrolysis_writer.dart` builds the payload; `crypto_signer.signRequestV2` signs the
canonical request — SHA-256 of the JSON body — at sync time). Nothing is signed per-sample.
Therefore **durability (surviving capture → upload) and cryptographic trust (proving origin at
upload) are cleanly separable concerns.** Today *both* the durability buffer and the pre-signing
assembly live in volatile RAM. The correct fix moves **only the durability buffer** into the
already-encrypted SQLCipher DB, leaving the signing step byte-identical. **No cryptographic
principle is touched** — we are moving a pre-signing buffer from RAM to encrypted disk.

**Insight B — for GPS, the cheap-phone fix is FREQUENCY, not ACCURACY.**
My first-pass "use `LocationAccuracy.medium`" would have been **wrong** and quietly dangerous:
on Android, geolocator's `medium` ≈ `PRIORITY_BALANCED_POWER_ACCURACY` (~100 m), which is
**coarser than the 10 m parcel-geofence buffer** the server corroborates against — it would
silently degrade anti-fraud below its tolerance. The real waste isn't accuracy; it's that a burn
day fires 15-30 *independent* high-accuracy cold fixes for captures **all taken at the same kiln,
within the same hour**. The fix is to acquire one high-accuracy fix and **reuse it** across nearby
captures — keeping 10 m accuracy (trust intact) while eliminating ~90% of GNSS activations.

---

## 1. How the burn pipeline works today (the trust model, precisely)

```
ESP32 (Health Thermometer 0x1809 / char 0x2A1C, ~2 Hz)
        │  raw °C doubles                 │  80-byte ECDSA attestation blobs (char a1b2c3d4…)
        ▼                                 ▼
BleTemperatureService (transport only)  ──► temperatureStream / attestationStream
        ▼
PyrolysisBleNotifier   (in RAM, whole burn)
  • liveCelsius   ← updated on EVERY raw sample (~2 Hz)          [HUD only, non-audit]
  • temperatureLog← decimated to 1 sample / 60 s                [the audit log]
  • attestationLog← appended on EVERY blob via [...list, blob]  [collected, see §5]
        ▼  (only at endBurn)
insertPyrolysisTelemetryWithOutbox():
  • writes PyrolysisTelemetry row to SQLCipher DB (encrypted at rest)
  • builds payload {temperature_readings, min/max, smoke_evidence(sha256s), hw_attestation, …}
  • enqueues it to SyncOutbox
        ▼  (later, when online)
SyncQueueManager → CryptoSigner.signRequestV2 (Ed25519 over SHA-256(body)) → POST /telemetry
        ▼
Backend: verify_signature → store → recompute_batch_credit derives min_temp SERVER-SIDE from
         temperature_readings (client min/max are advisory; server is the authority)
```

**Trust anchors (must remain intact):** (1) device Ed25519 signature proves *this device produced
these exact bytes*; (2) SHA-256 of each smoke/flame photo binds the evidence; (3) server
re-derives `min_temp` from the array, so the array must be preserved byte-for-byte; (4) SQLCipher
encrypts everything at rest. **None of these live inside the burn's RAM buffer** — they all act at
or after the outbox step.

---

## 2. Finding #1 — the burn's telemetry is RAM-only until `endBurn` (data-loss)

**Mechanism.** `temperatureLog` accumulates in `PyrolysisState` (RAM) for the entire 1-3 h burn
and is persisted only at `endBurn` (`pyrolysis_screen.dart:127`). There is **no incremental
persistence**.

**Why it fails on cheap phones — this is a *when*, not an *if*.** A 2-3 GB phone aggressively
kills backgrounded apps (operator opens WhatsApp → process reaped); a hot day + camera/GPS/BLE
drains a small battery flat mid-burn; heat-induced instability or any uncaught exception crashes
the process. **Any of these loses the entire burn's thermal curve** — the single most important
scientific proof that carbonization temperature was reached. Every *other* screen is protected by
the offline-first outbox (batch/moisture/dispatch commit to SQLite incrementally); the burn is the
lone exception, and it's the longest and least-repeatable operation (you cannot "re-run" a
3-hour burn).

**Design — incremental durable buffer, same encrypted DB, unchanged signing.**
1. New table `burn_sample_buffer` **inside the existing SQLCipher DB** (encrypted at rest, same key,
   no new plaintext surface): `(burn_session_uuid, batch_uuid, seq, celsius, sampled_at_iso)`, plus
   a `burn_session` row `(burn_session_uuid, batch_uuid, burn_start_iso, status)`.
2. In the notifier's decimation branch (the 1/min append), also **append one row** to
   `burn_sample_buffer`. Cost: one tiny insert per minute — negligible I/O even on slow eMMC.
3. `endBurn` assembles `temperature_readings` **from the buffer rows** (ordered by `seq`) — the
   array is byte-identical to today's in-RAM list — then signs + enqueues to the outbox exactly as
   now, and marks the `burn_session` `finalized`. The buffer rows can be pruned after the outbox
   row is durably committed (same transaction).
4. **Crash recovery:** on app launch, if a `burn_session` is `active` (never finalized), surface a
   "Resume/finalize interrupted burn" action on the dashboard that finalizes from the durable
   buffer. Worst-case loss is now **< 60 s**, not the whole burn.

**Security/trust analysis (why this preserves the core):**
- The buffer lives in the **same SQLCipher DB** → identical at-rest encryption; freed pages are
  ciphertext.
- Signing is still **once, at endBurn, over the assembled array** → canonicalization, the Ed25519
  signature, and the server's `min_temp` re-derivation are all **unchanged**. This is verifiable:
  the assembled `temperature_readings` must be byte-identical whether sourced from RAM or DB.
- **No new tamper surface.** An operator who controls the device could already edit the RAM buffer
  (freeRASP guards live tampering); the DB buffer requires the SQLCipher key and is equally
  pre-signing. The anti-fraud guarantees (device-origin signature, ESP32 hardware attestation once
  wired, server corroboration) all act *after* this buffer and do not move.
- **New invariant to enforce:** `burn_start`/`burn_end` come from the durable `burn_session` record,
  never re-stamped at resume; exactly one `active` session per batch; finalize is idempotent — so a
  resume can never splice two burns or forge a duration.

---

## 3. Finding #2 — whole-screen rebuild on every BLE sample, for the whole burn (sustained heat)

**Mechanism.** `pyrolysis_screen.dart:252` does `ref.watch(pyrolysisBleProvider)` on the **whole**
state; `_onTemp` sets `state = state.copyWith(liveCelsius: c)` on **every raw ~2 Hz sample**
(`pyrolysis_ble_notifier.dart:174`). Result: the entire screen's `build()` re-runs ~2×/s,
continuously, for hours — the worst sustained CPU+GPU pattern in the app, on its longest-lived
screen.

**Design — decouple the live HUD value from the audited state; do both:**
1. **Throttle the display update.** `liveCelsius` is explicitly HUD-only (the code comment: *"held
   in liveCelsius so the HUD shows realtime telemetry without polluting the persisted log"*). A
   human cannot read faster than ~1 Hz; throttle the `liveCelsius` state update to ≥ 500 ms. The
   raw stream still feeds min/max and the 1/min audit decimation unchanged.
2. **Narrow the watch.** The live-temperature widget watches
   `ref.watch(pyrolysisBleProvider.select((s) => s.liveCelsius))` so *only that Text* rebuilds when
   the value changes — not the chart, panels, and buttons. (`.select` limits rebuilds to when the
   selected field changes.)

Combined: the whole-screen rebuild storm is eliminated; the live readout stays smooth at ~1-2 Hz.

**Security/trust analysis:** `liveCelsius` is **display-only** and never part of the persisted or
signed payload (that's the 1/min-decimated `temperatureLog`). Throttling or narrowing the *display*
changes **nothing** in the audit log, the signature, or server corroboration. Zero trust impact.

---

## 4. Finding #3 — `LocationAccuracy.high` on every capture (bursty GNSS heat)

**Mechanism.** `location_service.dart:22` requests `LocationAccuracy.high` with a 12 s budget on
**every** evidence capture (moisture, each pyrolysis/flame photo, quench, density, day-start,
dispatch) — 15-30× per burn day, each a hot GNSS cold-fix, some burning the full 12 s under a tin
roof / tree cover.

**Design — reduce fix FREQUENCY, keep accuracy (see Insight B):**
1. Introduce a short-lived **GPS fix cache**: acquire one `LocationAccuracy.high` fix, cache it with
   a TTL (≈ 10 min) and reuse it for subsequent captures within the window. A burn's captures all
   happen at one kiln — one accurate fix represents them all.
2. **Movement guard:** before reusing, take a *coarse/last-known* fix (cheap) and, if it diverges
   from the cached fix by more than a small threshold, force a fresh high-accuracy acquisition. This
   prevents a stale fix from following a device that actually moved.
3. Refresh on TTL expiry, on movement, or on explicit failure — otherwise reuse.

**Security/trust analysis (why frequency-not-accuracy matters):**
- Accuracy stays **`high` (~10 m)**, so the server's parcel-geofence (10 m buffer) and
  EXIF-vs-claim mismatch checks keep their tolerance — a naive switch to `medium` (~100 m) would
  have silently broken them.
- The photo's EXIF GPS and the batch's claimed GPS are written from the **same cached `pos`**, so
  they still agree (the server's EXIF-vs-claim check detects a *swapped photo*, not fix *freshness*
  — a reused same-location fix is not a swap).
- Bound staleness (TTL) + movement guard so a cached fix can never misrepresent a *different*
  location. The mock-location flag and teleport corroboration are unaffected (still per-fix).

---

## 5. Adjacent issue surfaced by the trace: the attestation log (scope-guard)

`attestationLog` accumulates ESP32 ECDSA blobs via `[...state.attestationLog, blob]` on **every**
~2 Hz arrival → **O(n²)** list-copies and unbounded RAM growth over a multi-hour burn
(~21k blobs / 3 h) — **and `_endBurn` never passes them to the writer** (`attestationBlobs`
defaults to `const []`), so they are **collected and discarded**.

**Tier-1-scoped action (do):** decimate attestation collection to align with the 1/min sample
cadence (bounded, O(n), and it also survives via the §2 buffer if/when persisted). This kills the
O(n²)/RAM growth with zero trust change (nothing is persisted today anyway).

**Explicitly OUT of Tier-1 scope (note, don't do here):** actually persisting + signing the ESP32
hardware attestation would *strengthen* the trust chain (sensor-level proof, not just device-level)
— but it changes what's signed/verified and needs the ESP32 side confirmed. That is a separate
**trust-enhancement Part**, not a durability/thermal fix. Flag it; don't fold it in.

---

## 6. Cross-cutting security invariants (the "crypto canary" — must stay byte-identical)

Any implementation of §2-§4 MUST preserve, provably by test:
1. The assembled `temperature_readings` array (and thus SHA-256(body) and the Ed25519 signature) is
   **byte-identical** whether sourced from RAM (old) or the durable buffer (new).
2. The server's `recompute_batch_credit` derives the same `min_temp` → same credit → same
   `lca_signature`.
3. All pre-signing buffers remain inside SQLCipher (no plaintext file ever touches disk).
4. `burn_start`/`burn_end` are sourced from the durable record on resume — never re-stamped.
5. GPS accuracy delivered to EXIF + claim stays ≤ 10 m; mock-location + teleport signals unchanged.

---

## 7. Test strategy (test-first, per our discipline)

- **#1:** pure test that a payload assembled from buffer rows == payload assembled from an
  equivalent RAM list (byte-identical canonical JSON); a "kill mid-burn → relaunch → finalize"
  integration test asserting < 60 s loss and a valid signable payload; idempotent-finalize test;
  one-active-session-per-batch test.
- **#2:** notifier test that N raw samples within one throttle window produce ≤ 1 `liveCelsius`
  state emission but the 1/min audit decimation is unchanged; a widget test (rebuild counter)
  proving the whole screen no longer rebuilds per sample.
- **#3:** service test that two captures within TTL + no movement reuse one fix (one high-accuracy
  call); a captures-after-movement test forcing a fresh fix; a TTL-expiry refresh test.
- **Regression:** full three-suite green before + after; the existing pyrolysis/telemetry/LCA
  signature tests must pass unchanged (that *is* the crypto canary).

---

## 8. Sequencing & effort (independent estimate)

| Fix | Effort | Risk | Order |
|---|---|---|---|
| #1 durable burn buffer + crash-resume | Medium (Drift migration + notifier + resume UI) | Low (additive; signing untouched) | **First — it's the data-loss bug** |
| #2 throttle + `.select` HUD | Small | Very low (display-only) | Second |
| #3 GPS fix cache + movement guard | Small-Medium | Low (accuracy preserved) | Third |
| attestation decimation (§5) | Small | Very low | Fold into #1's notifier work |

Each is one commit, test-first, three-suite-verified, per standing discipline. #1 is not optional:
it is a credit-losing durability defect that the cheap-phone environment *will* eventually trigger.

**Nothing here weakens cryptography, evidence hashing, at-rest encryption, or server
corroboration — every fix operates strictly on the pre-signing/display/acquisition side of the
trust boundary.**
