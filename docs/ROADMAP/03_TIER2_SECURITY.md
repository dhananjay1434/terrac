# Tier 2 — Adversary-Ready: "Verifier-Defensible Security"

> **▶ Ready-to-run handoff:** a fully expanded, copy-paste-anchored execution prompt for this tier (every edit with exact code blocks, line anchors, test skeletons, commit plan, and traps) lives at [prompts/T2_EXECUTION_PROMPT.md](prompts/T2_EXECUTION_PROMPT.md). Give that file verbatim to the implementing engineer/agent.

> **Benchmark when this tier is green:** a rooted/emulated phone cannot mint evidence that reaches issuance; a captured request cannot be replayed; the admin secret cannot be brute-forced at wire speed; a decompiled APK doesn't hand an attacker the RASP-bypass map; and the on-screen PII can't be silently harvested. **Credits produced after this tier survive a hostile audit of the evidence chain.**
>
> **Total effort: ~1.5–2 weeks engineering** + one external dependency (Google/Apple attestation credentials).

Current strong base (don't touch, don't regress): Ed25519 frozen canonicals (server.py:392-487 ↔ crypto_signer.dart:100-137), timing-safe admin compares (server.py:562, 638, 675, 1744), batch-ownership guard `_assert_batch_ownership` (server.py:976-1014), path-traversal + size + SHA-256 guards on media (server.py:1309-1356), SQLCipher + secure storage + cert pinning + FreeRASP on the client.

---

## T2.1 — Real device attestation (the #1 credit-integrity gap) ⛔ partially external

- **Where:** `backend/server.py:189-197` (`_ATTESTATION_ENFORCED = False`), 755-767 (`attestation_verified = False  # TODO(security)…`). Client already collects and ships the blob.
- **Why:** today a rooted device's forged blob passes with a log warning. FreeRASP client checks are bypassable on-device by definition; only server-side verification of Google/Apple-signed verdicts closes this.
- **What (staged, so each step ships alone):**
  1. **Android — Play Integrity:** register the app in Play Console (needs T0.6 release signing first — Integrity verdicts bind to the signing cert). Backend: add `google-auth` to requirements; new module `backend/attestation.py` with `verify_play_integrity(token: str) -> AttestationVerdict` — decrypt/verify the JWE/JWS verdict (either via Google's `playintegrity.googleapis.com/v1:decodeIntegrityToken` server call or local key decryption), check `appIntegrity.appRecognitionVerdict == PLAY_RECOGNIZED`, `deviceIntegrity` contains `MEETS_DEVICE_INTEGRITY`, package name matches, `nonce` matches the request binding (see step 3).
  2. **iOS — App Attest/DeviceCheck:** same module, `verify_device_check(...)` verifying Apple's cert chain.
  3. **Nonce binding:** the attestation must be bound to the enrollment, not free-floating: client requests a server nonce at `/api/v1/register` time (extend `EnrollmentToken` with a `nonce` column, additive), passes it into the Play Integrity request, server checks the verdict's nonce. This kills replayed verdicts.
  4. **Rollout switch:** keep `_ATTESTATION_ENFORCED = False` while collecting real verdicts in the field (they persist to logs/audit); when the fleet is verified-capable, flip to `True` — from then on `attestation_ok=False` flows into `assemble()` (already wired, server.py:906) and unattested batches stay provisional. **Do not** make it reject uploads (provisional model, rule #2).
  5. Update `test_hardening.py` / add `backend/tests/test_attestation.py` with fixture verdicts (valid, wrong-package, wrong-nonce, expired).
- **Gate:** forged/absent blob ⇒ batch provisional with `attestation_unverified` reason when the flag is on; genuine device ⇒ non-provisional path unchanged.
- **Effort:** XL. **Blocked-by:** Play Console / Apple Developer credentials (cross-team). Everything except the credentials can be built and tested with fixtures now.

## T2.2 — Rate limiting (nothing throttles anything today)

- **Where:** `backend/server.py` app setup (near CORS, server.py:220-237).
- **What:** add `slowapi` (or a small middleware with an in-process token bucket now, Redis-backed at T3):
  | Route | Limit | Key |
  |---|---|---|
  | `POST /api/v1/register` | 5/min | IP |
  | `POST /api/v1/admin/*` + `GET .../compliance` | 30/min + exponential lockout on repeated bad `X-Admin-Secret` | IP |
  | `POST /api/v1/media` | 20/min | device_id |
  | other evidence endpoints | 120/min | device_id |
  Return 429 with `Retry-After`. Keep limits config-driven via env (`DMRV_RATELIMIT_*`) so the pilot can tune without a deploy.
- **Gate:** new `test_rate_limit.py` — 6th register call in a minute → 429; admin endpoint locks out after N bad secrets; legit device flow unaffected.
- **Effort:** M.

## T2.3 — Replay protection: signed timestamp freshness

- **Where:** canonical string builders — client `lib/services/crypto_signer.dart:100-137`, server `verify_signature` (server.py:392-434) and `verify_media_signature` (server.py:437-487).
- **Why:** signatures never expire; a captured request replays forever (idempotency only dedupes same-key retries — a replayed *different*-key capture still lands).
- **What (backward-compatible rollout — the canonical is FROZEN for deployed clients):**
  1. Add a header `X-Signed-At: <unix seconds>` and a **v2 canonical** that appends `\n<signed_at>`; client sends `X-Canonical-Version: 2`.
  2. Server: if `X-Canonical-Version: 2`, verify v2 canonical AND `abs(now - signed_at) <= 300s` (clock-skew window; make it env-tunable — rural devices drift). If absent, verify legacy v1 canonical (old fleet keeps working).
  3. After fleet upgrade, flip env `DMRV_REQUIRE_CANONICAL_V2=1` to refuse v1.
  4. Client: bump `crypto_signer.dart` to emit v2 + header; update the client-contract test (`backend/tests/test_client_contract.py`) and `test_signature.py` with v2 vectors; keep v1 vectors until the refuse-flag flips.
- **Gate:** replayed v2 request older than the window → 401; skewed-but-within-window → 200; v1 requests behave per flag.
- **Effort:** M/L (both sides + contract tests + staged rollout).

## T2.4 — R8/ProGuard + obfuscation on Android

- **Where:** `android/app/build.gradle.kts` (no `minifyEnabled` today), new `android/app/proguard-rules.pro`.
- **What:**
  ```kotlin
  release {
      signingConfig = signingConfigs.getByName("release")
      isMinifyEnabled = true
      isShrinkResources = true
      proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
  }
  ```
  Rules file: keep rules for flutter embedding, Drift/sqlite3 NDK, flutter_secure_storage, sentry, freeRASP (Talsec publishes required -keep rules), flutter_reactive_ble, workmanager. Build with `flutter build apk --release --obfuscate --split-debug-info=build/symbols` and archive `build/symbols` per release (Sentry needs them to symbolicate).
- **Gate:** release build runs the full capture→sync flow on a phys device; Sentry test-crash symbolicates; `jadx` on the APK shows obfuscated app classes.
- **Effort:** M (expect one round of missing -keep rules). **Depends on:** T0.6.

## T2.5 — Screenshot/recents protection (`FLAG_SECURE`)

- **Where:** `android/app/src/main/kotlin/.../MainActivity.kt` (or via a plugin) + iOS scene snapshot masking.
- **What:** set `WindowManager.LayoutParams.FLAG_SECURE` in `MainActivity.onCreate` (blocks screenshots + recents thumbnail). Gate it on the same release-mode check the RASP uses so debug screenshots still work for development. iOS: blur the snapshot in `sceneWillResignActive`.
- **Gate:** screenshot attempt on release build fails; recents view is masked.
- **Effort:** S.

## T2.6 — Health endpoint that tells the truth + secret-entropy floor

- **Where:** `/api/health` (server.py:379-385); `_require_secret()` (server.py:173-184).
- **What:**
  1. Health: run `SELECT 1` through `get_session`; return `{"status":"ok","db":"ok"}` or 503. Keep it unauthenticated but response-minimal.
  2. `_require_secret`: enforce a floor — reject secrets `< 32` chars / obviously low-entropy (`len(set(value)) < 10`) with a clear RuntimeError. (This was already planned as "P2.a extends this" in the code comment — finish it.) Keep CI literals working by floor-exempting when `DMRV_DISABLE_DOTENV=1`? **No** — instead update conftest/CI to 32-char test secrets in the same PR; several tests assert the exact literal, so change both together (`backend/tests/conftest.py`, `.github/workflows/backend-ci.yml`).
- **Gate:** `test_p1_25_lifespan.py`-style test: DB down → 503; short secret → refuses to boot.
- **Effort:** S/M.

## T2.7 — EXIF/GPS corroboration honesty pass

- **Where:** `_evaluate_anchor` + GPS mismatch threshold (server.py:131-170, 1 km constant at ~server.py:152).
- **Why:** the client *writes* the EXIF itself (secure_capture_service.dart:30-43), so server-side EXIF checks corroborate the client against the client. It still catches sloppy fraud and honest mistakes — keep it — but stop treating it as strong evidence.
- **What:**
  1. Extract `1.0` km into a named constant `GPS_ANCHOR_MISMATCH_KM` with a comment stating the trust model explicitly ("client-authored EXIF: weak corroboration; attestation (T2.1) is the strong control").
  2. Add the batch-creation plausibility signals (`mock_location_enabled`, the 150 km/h movement check at server.py:1157) into the audit JSON so a verifier sees them per batch.
  3. Cross-device corroboration (supervisor-visit GPS vs batch GPS) as a *future* audit-only signal — file it, don't build it (needs field process design first).
- **Gate:** audit JSON carries the signals; constant named; no behavior change otherwise.
- **Effort:** S.

## T2.8 — Rotate the exposed dev HMAC secret at first deploy

- **Where:** `backend/.env` on this machine (not git-tracked — verified — but it has lived in a Downloads folder on an unencrypted laptop).
- **What:** at first real deployment, generate fresh `DMRV_HMAC_SECRET` + `DMRV_ADMIN_SECRET` (32+ random bytes, base64url), store in the deploy platform's secret manager, never in a file. Note: rotating the HMAC secret invalidates *nothing* device-side (devices use Ed25519 keys) but re-signs future LCA audits — old `lca_signature` values verify only against the old key, so archive the old key material securely for verification of already-issued batches, or re-sign historical audits in a migration.
- **Effort:** S + a decision on historical signatures.

---

## ✅ Tier 2 exit criteria (the benchmark, verbatim)

- [ ] With `_ATTESTATION_ENFORCED=True`, a forged attestation batch is provisional; fixture-tested.
- [ ] `for i in $(seq 10); do curl -X POST .../register; done` → 429 before 10.
- [ ] A byte-identical replay of a captured v2 request 10 minutes later → 401.
- [ ] `apksigner` shows release cert; `jadx` output is obfuscated; screenshots blocked on release builds.
- [ ] `/api/health` fails when the DB fails; server refuses weak secrets.
- [ ] Trust model of every evidence signal written down next to its code.

**Credits minted after this tier can be defended in front of a hostile technical auditor: every evidence signal has a stated trust level and the strong ones are cryptographic.**
