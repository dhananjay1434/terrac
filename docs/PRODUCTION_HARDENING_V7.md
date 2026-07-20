# PRODUCTION HARDENING V7 — Fix the Real Problems (phased)

## PURPOSE

An independent, code-verified audit (not the stale .md docs) found the system's
security, auth, credit math, and issuance controls are **genuinely solid**. The
real remaining problems are narrower and specific. This document fixes them
one phase at a time — each phase is self-contained, test-gated, and independently
shippable. Execute ONE phase, run its gate, report back, then wait for go.

Context: distribution is **private B2B APK** (no Play Store). CI is intentionally
off (GitHub limits) — do NOT re-add it; the release gate is the per-phase test
run in this doc.

## GLOBAL RULES

1. Read every target file verbatim before editing; match exactly.
2. One phase per turn. After a phase: run its gate, commit with the given
   message, then STOP and report — do not roll into the next phase.
3. Gate commands per component:
   - App: `flutter analyze <changed files>` + `flutter test <test files>` then full `flutter test`.
   - Backend: `python -m pytest <test files>` then full `python -m pytest`.
   - Portal: `npm test -- --run` + `npm run typecheck` + `npm run build`.
4. Do NOT push. The user pushes.
5. Where a phase needs a decision only the user can make (credentials, a
   methodology choice), the phase says **NEEDS USER INPUT** — stop and ask
   before implementing that part.
6. Logic-freeze inside each phase: change only what the phase scopes. If an
   unrelated test breaks, you changed too much — revert and narrow.

## PRIORITY ORDER (why this sequence)

1. **P1 RASP self-brick** — the private APK literally won't start until fixed. Nothing else matters if the app hard-locks on the customer's phone.
2. **P2 Sync failure visibility** — farmers silently lose data today. Direct income/trust harm.
3. **P3 GPS anti-fraud bypass** — auditor's trust; a fraud hole open right now.
4. **P4 Attestation enforcement** — auditor's #1 question; needs user decision on credentials.
5. **P5 Portal token storage** — real but lower-severity web-security hardening.
6. **P6 Farmer-fairness surfacing** — under-credit reasons + moisture-count clarity (optional polish).

---

## PHASE 1 — Fix the RASP self-brick (private-distribution blocker)

**Problem (verified):** `lib/services/device_integrity_service.dart` hard-locks
the app when either fires:
- `onUnofficialStore` (line ~59) — triggers on ANY non-Play-Store install. Your
  entire distribution model is sideload/direct-APK/MDM, so this locks every
  legitimate install.
- Package/cert mismatch — Talsec config declares `packageName: 'com.kontiki.dmrv'`
  and `bundleIds: ['com.kontiki.dmrv']` (lines ~38-41) but the real Android
  `applicationId` is `io.dmrv.dmrv_app` (android/app/build.gradle.kts:38). A
  mismatch trips `onAppIntegrity` → hard-lock.

**Files:** `lib/services/device_integrity_service.dart`,
`test/device_integrity_test.dart` (extend), `android/app/build.gradle.kts` (read only — confirm applicationId).

**Changes:**
1. **Reconcile the package identity.** Decide the ONE true release identity.
   Recommended: keep the existing `io.dmrv.dmrv_app` (changing applicationId
   orphans installed DBs, per the build.gradle comment). Update the Talsec
   `AndroidConfig.packageName` to `io.dmrv.dmrv_app` and set the correct
   iOS bundle id if iOS is in scope (else leave iOS config but it won't run on
   Android). **NEEDS USER INPUT:** confirm the final applicationId + iOS bundle
   id before editing — this must match the real signed build forever.
2. **Neutralize `onUnofficialStore` for private distribution.** Two options —
   ask the user which:
   - (a) Remove the `onUnofficialStore` callback entirely (private APKs are
     never from a store; the check is meaningless here).
   - (b) Keep it but make it log-only (not `_compromised`), so a genuine
     repackage still shows in telemetry without bricking legit sideloads.
   Recommended: **(b)** — keeps the signal, removes the brick.
3. Keep every OTHER threat callback (root, hooks, debugger, emulator,
   app-integrity, device-binding) wired to `_compromised` — those are the real
   anti-tamper value and must stay.

**Tests to create/extend** in `test/device_integrity_test.dart`:
- A test asserting the Talsec config's `packageName` equals the release
  `applicationId` string (`io.dmrv.dmrv_app`) — a regression guard so the
  mismatch can never silently return. (Assert on the constant/config the
  service builds; refactor the config into a pure testable factory if needed.)
- A test asserting `onUnofficialStore` does NOT set
  `deviceCompromisedProvider`/`isDeviceCompromisedGlobally` true (i.e. a
  sideloaded install is not treated as compromised), while a root/hook threat
  STILL does.
- Confirm the existing `test/remediation/device_integrity_enforcement_test.dart`
  still passes unchanged (fail-closed on missing cert hash must remain).

**Gate:** `flutter analyze lib/services/device_integrity_service.dart test/device_integrity_test.dart` then `flutter test test/device_integrity_test.dart test/remediation/device_integrity_enforcement_test.dart` then full `flutter test`.

**Commit:** `fix(app): stop RASP hard-locking legit sideloaded installs; align package identity`

---

## PHASE 2 — Sync failure visibility + force-retry (farmer trust)

**Problem (verified live):** a submission that fails to sync retries with
exponential backoff (`1 << retryCount`, up to `retryCount > 10` →
`FAILED_PERMANENTLY`). The failure reason IS stored (`failureReason` column,
`sync_queue_manager.dart:627/645`) and `retryPermanentlyFailed` exists — but:
- A PENDING-in-backoff row (what the farmer saw as "1 pending") shows NO reason
  and the user cannot force it to retry now (only FAILED_PERMANENTLY rows can be
  reset via `retryAllPermanentlyFailed`).
- The dashboard's top "N pending" indicator doesn't route the user to the reason.

**Files:** `lib/services/sync_queue_manager.dart`,
`lib/ui/screens/sync_health_screen.dart`,
`lib/providers/sync_providers.dart` (as needed),
`test/sync_two_phase_test.dart` or a new `test/sync_retry_visibility_test.dart`,
`test/ui/screens/` (widget test if a screen changes).

**Changes:**
1. **Surface the reason on backoff rows too.** `watchProblemRows()` already
   includes `PENDING` rows with `retryCount > 0`. Ensure the Sync Health screen
   renders `failureReason` for those (not just FAILED_PERMANENTLY). If a PENDING
   backoff row currently shows no reason, display the last `failureReason` +
   a human "waiting to retry (attempt N)" line.
2. **Add a manual force-retry for backoff PENDING rows.** Add a method
   `retryNow(operationId)` (or extend the existing retry) that clears the
   backoff gate — reset `lastAttemptAt`/`retryCount` enough to make the next
   loop attempt immediately — and kicks sync. Wire a "Retry now" button in Sync
   Health for backoff rows (the FAILED_PERMANENTLY "Retry" already exists).
   LOGIC-FREEZE: do not change the backoff formula or the max-retry ceiling;
   only add an operator-initiated immediate-retry path.
3. **Make the dashboard pending indicator actionable.** If there is a stuck or
   backing-off row, the dashboard's pending affordance should route to Sync
   Health (so "1 pending" is never a dead end). Keep it presentational.

**Tests to create:**
- `test/sync_retry_visibility_test.dart`:
  - a PENDING row with `retryCount > 0` and a `failureReason` is returned by
    `watchProblemRows()` (already true — assert it) AND the reason is non-null
    after a simulated failed attempt.
  - `retryNow(op)` resets the backoff gate so the next `_processPending` attempts
    the row instead of skipping it (assert it's no longer skipped).
- Widget test (if screen changed): Sync Health shows the reason text + a
  "Retry now" control for a backoff row.
- Existing `test/sync_two_phase_test.dart` and `test/sync_deadlock_test.dart`
  must pass unchanged.

**Gate:** analyze changed files, run the sync tests, then full `flutter test`.

**Commit:** `feat(app): surface sync failure reason on backoff rows + operator force-retry`

---

## PHASE 3 — Close the no-EXIF GPS anti-fraud bypass (auditor trust)

**Problem (verified):** `backend/geo.py:86` — a photo with NO EXIF GPS
short-circuits `_gps_mismatch_km` and the batch is STILL upgraded. Stripping
EXIF evades location corroboration entirely. Documented as "attestation is the
backstop," but attestation is currently off (Phase 4), so both fraud layers are
down.

**Files:** `backend/geo.py`, `backend/corroboration.py` (where geo feeds the
gate, if applicable), `backend/tests/test_gps_corroboration.py` (extend),
`backend/tests/remediation/test_mock_gps_server_side.py` (confirm still passes).

**Changes — NEEDS USER INPUT (methodology decision):** pick one policy for
"photo has no EXIF GPS":
- (a) **Treat missing GPS as non-corroborating** — the batch does not get the
  GPS-corroborated upgrade (stays provisional on that axis) rather than passing
  by default. Most defensible to an auditor.
- (b) **Quarantine for review** — flag the batch for manual verifier review.
- (c) **Keep current behavior but make it explicit + logged + surfaced** in the
  compliance output so an auditor sees "GPS not verified (no EXIF)" rather than
  a silent pass.
Recommended: **(a)** with the reason surfaced in the compliance reasons list.

**Tests to create/extend** in `test_gps_corroboration.py`:
- a media item with EXIF GPS matching the batch → corroborated (unchanged).
- a media item with EXIF GPS mismatched > threshold → quarantined/rejected
  (unchanged).
- **NEW:** a media item with NO EXIF GPS → under the chosen policy (a/b/c),
  assert the batch is NOT silently upgraded / carries the explicit reason.
- Regression: `test_mock_gps_server_side.py` still passes (mock-location
  detection unaffected).

**Gate:** `python -m pytest backend/tests/test_gps_corroboration.py backend/tests/remediation/test_mock_gps_server_side.py` then full `python -m pytest`.

**Commit:** `fix(backend): no-EXIF-GPS photo no longer silently corroborates a batch`

---

## PHASE 4 — Turn on device attestation (auditor's #1 question)

**Problem (verified):** `backend/credit_engine.py:183` — with
`DMRV_ATTESTATION_ENFORCED` off (default), `attestation_ok` is always true, and
the Play Integrity provider verifier (`backend/attestation.py`
`verify_play_integrity`) has no real Google credentials wired. So root/emulator/
tampered devices are not blocked server-side today.

**This phase is staged and NEEDS USER INPUT — do not implement blindly:**
1. **Decision 1 — credentials.** Real enforcement requires a Google Play
   Integrity project (decrypt/verify the verdict token) OR the Android
   hardware-key-attestation path. Ask the user: do they have (or want to set up)
   Play Integrity credentials? Without them, enforcement can only reject
   everything (useless) or accept everything (current). There is no middle.
2. **Decision 2 — rollout.** The code already has a grace-window path
   (`attestation_in_grace`) so enabling enforcement doesn't instantly brick an
   existing fleet. Confirm the grace window length.

**Files (once decided):** `backend/attestation.py` (wire the real verifier),
`backend/credit_engine.py` (enforcement already coded — just flip the env +
confirm the grace path), env config (`render.yaml` / deploy),
`backend/tests/test_p4_1_attestation.py` + `test_attestation.py` (extend).

**Changes (after user decision):**
- Wire `verify_play_integrity` to the real provider (or the chosen attestation
  source), keeping it behind the existing interface so tests inject doubles.
- Set `DMRV_ATTESTATION_ENFORCED=1` in the production env (NOT in test config).
- Confirm the app actually SENDS `hw_attestation` in telemetry
  (`tel_payload.get("hw_attestation")`) — verify the Flutter side populates it;
  if not, that is a sub-task (app must attach a fresh Play Integrity token per
  submission, bound to `signed_at` per the attestation.py nonce note).

**Tests to create/extend:**
- enforced + verified verdict → `attestation_ok` true, batch issuable.
- enforced + unverified + device OUT of grace → batch provisional
  (`attestation_unverified` reason present).
- enforced + unverified + device IN grace → provisional-but-tolerated per policy.
- nonce/replay: a verdict with a stale/mismatched nonce → rejected
  (`nonce_mismatch`).
- app-side (if changed): telemetry payload includes a non-empty `hw_attestation`.

**Gate:** the attestation tests then full backend suite; if app changed, full `flutter test` too.

**Commit:** `feat(backend): enforce device attestation with Play Integrity + grace window`

---

## PHASE 5 — Portal token storage hardening (web security)

**Problem (verified):** `portal/src/auth.ts` stores the bearer token in
`localStorage` — readable by any injected script (XSS-stealable). React escaping
keeps the surface small, but it's the one real web-security gap.

**Files:** `portal/src/auth.ts`, `portal/src/api.ts` (token attach),
possibly `backend/portal/routes.py` (if moving to httpOnly cookie),
`portal/src/**/__tests__/` auth-related tests.

**Changes — NEEDS USER INPUT (pick the model):**
- (a) **httpOnly cookie** (strongest): backend sets the session as an httpOnly,
  Secure, SameSite cookie on login; portal stops storing the token in JS; API
  calls rely on the cookie. Requires a backend change + CORS/credentials config.
- (b) **sessionStorage + short TTL** (lighter): reduces persistence (cleared on
  tab close) but still JS-readable — a smaller mitigation, not a fix.
- (c) **in-memory only** (no persistence): most XSS-resistant of the JS options,
  but the user re-logs on every refresh.
Recommended: **(a)** for a system issuing credits; **(c)** if backend changes
are out of scope this round.

**Tests to create/extend:**
- login stores/attaches the token per the chosen model; a 401 clears session
  and redirects (existing behavior preserved).
- if httpOnly: backend test that `/login` sets the cookie flags
  (HttpOnly, Secure, SameSite) and that an authed request works via cookie;
  portal test that the token is no longer in `localStorage`.

**Gate:** portal `npm test -- --run` + `npm run typecheck` + `npm run build`;
if backend changed, backend suite too.

**Commit:** `fix(portal): move portal session off localStorage to reduce XSS token theft`

---

## PHASE 6 — Farmer-fairness surfacing (optional)

**Problem (verified):** two silent under-credit paths hurt farmers with no
explanation:
1. Missing BLE thermocouple data → `min_recorded_temp_c` defaults to 0 → fails
   the methane-compliance check → 30 kg/t penalty (`lca_engine.py:187`). Safe
   for the auditor (conservative) but the farmer sees a low credit and no reason.
2. C2 needs ≥10 photographed moisture readings
   (`corroboration.py:132`); a batch with fewer sits PROVISIONAL forever. If the
   capture UI doesn't make the target unmistakable, farmers under-document and
   go unpaid.

**Files:** `backend/corroboration.py` / compliance reason surfacing (ensure the
specific reason is emitted), portal `ComplianceChecklist` (already renders
reasons — confirm these two are human-readable), Flutter
`moisture_verification_screen.dart` (make the "X of 10 required" target loud).

**Changes:** additive/UX only — no math or gate-threshold changes.
- Ensure the compliance output carries a clear, human reason for the methane
  penalty (e.g. "burn temperature not recorded → methane penalty applied") and
  for insufficient moisture samples (already `insufficient_moisture_samples` —
  confirm the portal renders a human label).
- In the moisture capture screen, show the running "N of REQUIRED" prominently
  and block/ warn before the batch can be considered complete.

**Tests:** portal checklist test renders human labels for both reasons; app
widget test shows the required-count target. Full suites green.

**Commit:** `feat: surface under-credit reasons to farmers (temp-missing penalty, moisture count)`

---

## AFTER EACH PHASE — report format

Report back with: what changed (files), test results (X passed / Y failed),
any NEEDS-USER-INPUT decision made or still pending, and the commit hash.
Then STOP and wait for the go on the next phase.
