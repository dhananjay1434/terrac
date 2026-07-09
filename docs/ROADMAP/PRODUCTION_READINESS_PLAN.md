# PRODUCTION MASTER PLAN — dMRV from demo to deployable product (v2)

**Date:** 2026-07-09 · **Basis:** three fresh line-level deep audits (backend internals, client/services internals, release & infra engineering) + the criterion-level COMPLIANCE_GAP_REPORT.md + the demo-shortcut inventory. Every finding carries file:line evidence from the audits; severities below are my own judgment after reviewing each (a few agent ratings were adjusted — noted where it matters).

---

## 0. Executive verdict

The **architecture is right** — offline-first outbox, device-held Ed25519 keys, hash-anchored evidence, a pure-function compliance engine, provisional-only gating. Three audits independently confirmed the bones are production-grade. What's missing is what separates a strong pilot from a product:

1. **Recovery paths.** The app is excellent at capturing and terrible at recovering: stranded sync rows are invisible, a lost passphrase is unrecoverable, a killed app orphans half-batches, a wrong clock locks a device out forever.
2. **Robustness fine print on the server.** Unguarded JSON parses, a race-fallback that skips one validation, naive/aware timezone mixing, N+1 recomputes — none visible in a demo, all visible at 200 devices.
3. **Field completeness for Rainbow.** A batch cannot reach issuable from the phone: one genuine shape bug (moisture) + six missing capture screens.
4. **Release engineering.** Debug-signed releases, unvalidated R8/ProGuard, no Flutter CI lane, undeclared backend deps, no deployment.
5. **The human side of the loop.** Labs, verifiers, and admins have curl, not a product. The portal is where the credit actually gets issued.

---

## 1. Engineering-fix backlog (consolidated, ranked, phase-tagged)

### P — CRITICAL (fix before any real user; most are P0/P1)

| ID | Finding | Where | Phase |
|---|---|---|---|
| C1 | **No git remote** — the entire company fits on one laptop | repo | P0 |
| C2 | **Debug keystore signs release builds** (`signingConfig = debug`, build.gradle.kts:44) | android | P0 |
| C3 | **FAILED_PERMANENTLY sync rows are invisible** — evidence silently stranded with no operator recovery (sync_queue_manager.dart:260,365,465) | client | P1 |
| C4 | **Passphrase loss = total local data loss**, zero recovery (passphrase_resolver.dart) — mitigations: prompt sync, server-side batch recovery for re-enrolled devices, optional recovery code | client | P1 |
| C5 | **Half-batch orphaning on app kill** — `findIncompleteBatch` misses states; resume doesn't restore session/statuses (dashboard_provider.dart:86-97) | client | P1 |
| C6 | **Unguarded `json.loads` in recompute** — one corrupt payload bricks a batch's credit path (server.py:927-929,964,982,1018,2289) | backend | P1 |
| C7 | **Race-fallback in create_batch doesn't validate `batch_uuid`** — cross-batch acceptance possible under idempotency collision (server.py:1428-1441); add row-level guard + validate uuid in fallback | backend | P1 |
| C8 | **Secrets hygiene**: demo admin/HMAC secrets in `demo_tools/*.bat`, verifier URL, `.env`; HMAC rotation breaks all historical `lca_signature`s with no key-versioning | repo/backend | P0 (rotate) + P3 (key versioning) |

### H — HIGH (breaks under real load / real field conditions)

| ID | Finding | Where | Phase |
|---|---|---|---|
| H1 | Timezone naive/aware mixing in teleport + comparisons (server.py:1379-1387) — normalize all datetimes to aware-UTC at the boundary | backend | P1 |
| H2 | N+1 + repeated recompute: 8+ queries × per-evidence-POST recompute; loop-parsing JSON per row (server.py:912-1076) — batch the reads, debounce recompute | backend | P3 |
| H3 | Blocking `json.loads` of 100k-float telemetry on the event loop (server.py:927) — `asyncio.to_thread` for large payloads | backend | P3 |
| H4 | UUID type split: `batches.batch_uuid` is PG_UUID, all six evidence tables are String(36) — joins rely on string form staying canonical; normalize at write, add a migration-time consistency check | backend | P1 |
| H5 | BLE disconnect mid-burn: no `onError` on temp/conn streams; operator gets no warning, telemetry silently truncated (pyrolysis_ble_notifier.dart:100) | client | P1 |
| H6 | Clock-skew lockout: v2 signing + wrong device clock → every retry 401 → FAILED_PERMANENTLY; no detection or "fix your clock" surface (crypto_signer.dart:150) | client | P1 |
| H7 | Evidence-file GC race: stamp/delete ordering can strand a row as FAILED_PERMANENTLY with the file already deleted (sync_queue_manager.dart:565-575) | client | P1 |
| H8 | Smoke-photo count stranding: END BURN persist throws "need 4, found 3" with no way back (pyrolysis_writer.dart:159; screen doesn't pre-validate) | client | P1 (folds into pyrolysis screen rework) |
| H9 | Sentry DSN empty → production crashes black-holed; no release-build guard (main.dart:34) | client | P0 |
| H10 | Backend deps undeclared: `cryptography`, `python-dotenv` imported but not in requirements.txt | backend | P0 |
| H11 | **No Flutter lane in CI** (no analyze/test/build of the app anywhere) | CI | P0 |
| H12 | ProGuard keep-rules gaps (camera/CameraX, image/exif paths) + release R8 build never validated + 16 KB page-size alignment (Play requirement; warning already seen on-device) | android | P0 |
| H13 | Android manifest/background contract unverified: workmanager periodic sync + geolocator foreground service vs Android 13+ notification permission & battery optimization — must be tested on real device in release mode (agent flagged missing POST_NOTIFICATIONS etc.; verify empirically rather than cargo-cult adding) | android | P0/P1 |
| H14 | Admin lab channels are HMAC-secret-only (no signature, no per-actor identity/audit) — acceptable for pilot, must become role-authenticated portal API (server.py:802,836) | backend | P2 |
| H15 | Temp-plausibility gap: credit uses `min_recorded_temp_c` without re-validating against the ≥60-sample log; plus no cross-field plausibility (temp×moisture×yield) | backend | P4 (methodology-adjacent) |

### M — MEDIUM (ops pain / correctness fine print)

| ID | Finding | Phase |
|---|---|---|
| M1 | Rate-limit dict clear-all at 4096 (evasion window + lost counters) — prune per-window instead (server.py:386) | P3 |
| M2 | Media path guard runs after file write; no cleanup of the partially-written file (server.py:1580-1589); also sanitize `device`/`op` before path build | P1 |
| M3 | Enrollment tokens: no entropy/length floor at mint; pair with QR-minting in portal (server.py:727) | P2 |
| M4 | Missing `max_length`/range validators on several payload strings (e.g., feedstock_species) | P1 |
| M5 | Admin endpoint idempotency inconsistent (kiln/annual upsert vs training/visit insert-only) | P2 |
| M6 | Docker: no `.dockerignore`, no docker-compose committed; healthcheck start-period tight for first-boot migrations | P3 |
| M7 | Two-phase sync invariant (media payload must have photoPath) enforced at sync time, not insert time | P1 |
| M8 | Batch-per-table unique constraints forbid re-burn/corrective flows — decide policy (tombstone/supersede) with methodology owner | P4 |
| M9 | iOS: deployment target/pods/CI unvalidated; explicitly de-scope iOS until P5 or a customer demands it | P5 |
| M10 | pubspec caret ranges vs lock — adopt "lock is law in CI; pin before release branch" policy | P0 (policy) |
| M11 | Ruff non-blocking with ~100 legacy issues; analyzer infos in legacy files | P4 |
| M12 | Passphrase migration edge (crash between secure-storage write and prefs remove) | P1 (with C4 work) |
| M13 | BLE pairing whitelist stored unhashed in secure storage (root-level tamper) — document threat model; hash if cheap | P4 |
| M14 | Cleanup manifest retries undeletable files forever — cap retries | P4 |
| M15 | Android `applicationId` TODO + FLAG_SECURE release-gate verification | P0 (with release build) |

### Explicitly de-prioritized (agent flagged, I disagree or defer)
- "Idempotency collision attack" as CRITICAL → requires a validly-enrolled signing device; mitigated by C7's uuid validation + per-device scoping later. HIGH→ folded into C7.
- "iOS 13.0 target won't pass review" → overstated; iOS is de-scoped to P5 regardless (M9).
- Caret versioning as HIGH → normal Flutter practice; handled as policy (M10).

---

## 2. Rainbow field completeness — the screen build list (P1)

From COMPLIANCE_GAP_REPORT.md; unchanged and confirmed by the client audit. Order = dependency + impact:

1. **Moisture multi-reading loop** — THE bug: app stores one `moisture_percent`; the C2 gate counts `moisture_readings` rows (≥ max(10, ⌈kg/100⌉), each photographed). Counter-hero UX; writes N rows + photos. *Nothing can pass C2 until this ships.*
2. **Biomass input** — weight + method (direct-weigh / yield-conversion) on Sourcing; drives C2's dynamic threshold and C1.
3. **Kiln selection** — pick/scan registered kiln at burn start → `kiln_id`, `kiln_type`, real capacity (kills the 200 L + `WATER_QUENCH` hardcodes). Activates C0/C3/C3b/C9-PAH which are silently inert today.
4. **Pyrolysis completion rework** — flame-height (open, <0.5 m) + ignition energy (closed); **align stage names** (app's `smoke_0/50/90/100` vs gate's `flame_curtain/quenching/flame_height` — one side must change; decide with methodology owner); pre-validate photo count before END BURN (fixes H8).
5. **Composite sample screen** — photo + kiln QR + batch QR → `composite_pile_samples`. Also the physical key for the lab flow (§3).
6. **Delivery & buyer fields** on End-Use — date, amount, buyer name/contact (C5 columns exist, UI doesn't).
7. **Sync health screen** — pending/synced/stuck with human reasons + retry (fixes C3); includes clock-skew warning (H6).
8. **Enrollment screen** — first-launch token entry/QR scan (kills compile-time tokens); project linkage provisioned at enrollment, not dart-define.
9. **Batch checklist hub** *(P4, the UX spine)* — per-batch checklist mirroring the server compliance list; resumable, non-linear; fixes the resume UX permanently (C5's product-level answer).
10. *(Deferred)* Transport legs screen — after Rainbow supplies fuel factors.

---

## 3. Lab & Verifier portal (P2)

One web app, three server-enforced roles: **project admin** (registries, tokens, issuance), **lab technician** (find batch → submit results + certificate only), **verifier** (read-only).

- **Foundation:** T3.4 read API — `GET /admin/batches` (cursor pagination, filters), `GET /admin/batches/{uuid}` (evidence counts + audit), `GET /admin/devices`, `GET /admin/summary`. Everything else builds on it. Replaces the demo page's secret-in-URL pattern (C8) with real auth.
- **Batch dashboard + detail:** the premium verifier aesthetic already built, plus evidence timeline and photos via short-lived presigned URLs (needs object storage, never file paths).
- **Lab entry — the chain-of-custody gem:** field composite sample photographed *with the batch QR* → physical sample travels with that QR → lab tech **scans QR → lands on the batch** → enters H:Corg/Corg/moisture-samples/bulk-density (+ inertinite/Ro for 1000-yr) → uploads signed certificate PDF → recompute fires → `assumed_*` flip green live → credit recalculates from lab values. Physical sample ≡ digital batch.
- **Registry forms** for today's curl-only endpoints: kilns, scale calibrations, operator training, supervisor visits, annual verification, token minting (as QR for the enrollment screen). Fix M5 idempotency while building.
- **Issuance:** deliberate human "Issue credit" action when all gates green — immutable audit event, actor identity, timestamp. The only place "ISSUED" ever appears.

---

## 4. Infrastructure & deployment (P3)

1. Commit Dockerfile + add `.dockerignore` + docker-compose (api + postgres + minio) — image-boot smoke in CI.
2. Host decision: **Cloud Run + Cloud SQL + GCS** (least-ops for pilot fleet). TLS with SPKI/intermediate pinning so cert renewals don't brick the fleet (`DMRV_PINNED_CERT_PEM` rotation policy documented).
3. Postgres in prod (path already validated by T3.1, incl. the two PG bugs already fixed).
4. **Object storage for evidence** (T3.3): storage abstraction Local/S3, bucket versioning + object lock; migrate pilot uploads. Evidence must survive host death.
5. **Observability** (T3.5): JSON logs + request IDs, `/metrics`, Sentry both sides (fix H9 with a release guard), alerts: 5xx, p95, provisional-ratio spike, health.
6. **Backups + tested restore drill** (T3.6); RPO 24h / RTO 2h documented.
7. **HMAC key versioning** (C8b): `key_id` recorded with every `lca_signature`; old keys archived for historical verification before any rotation.
8. Recompute efficiency (H2/H3) + rate-limit pruning (M1) + load smoke test at 200 devices (T3.8).

---

## 5. Release engineering (P0 thread)

- Real keystore + signing config (C2); CI secret-managed. `applicationId` finalized (M15).
- First **validated** release build: R8/obfuscate + ProGuard gaps closed (H12) — install on real device, walk full flow, verify FLAG_SECURE, camera, BLE, secure storage, workmanager under release constraints (H13 verified empirically: Android 13+ notifications, battery optimization, boot persistence).
- **16 KB page-size compliance**: upgrade Flutter/AGP/NDK as needed until the on-device warning is gone (Play hard requirement).
- CI: Flutter lane (analyze + test + release-apk build) (H11); backend deps pinned (H10); dependency policy M10; tag-driven release later (P4).

---

## 6. Test strategy (closing the audits' named holes)

- **Backend:** tests for corrupt-payload recompute (C6), tz-mixed teleport (H1), race-fallback uuid validation (C7), media path sanitization (M2), payload validator bounds (M4). Keep suite gates green (307+/1).
- **Client:** unit tests for sync-queue failure modes — FAILED_PERMANENTLY surfacing, JSON-synced-media-lost retry, GC ordering (C3/H7/M7); clock-skew detection (H6); passphrase migration (M12); resume logic (C5).
- **Integration (new `integration_test/`):** cold start → full batch → kill mid-flow → resume → offline capture → reconnect → sync green. BLE-disconnect-mid-burn with fake source (H5).
- **Goldens:** 9 screens on the India skin (locks the token system before the Europe skin work).
- **Release checklist test:** scripted on-device release-mode pass (H12/H13) per release.

---

## 7. Phased execution

| Phase | Contents (IDs) | Effort | Exit gate |
|---|---|---|---|
| **P0 — Protect & release-able** | C1, C2, C8-rotate, H9, H10, H11, H12, H13-verify, M10, M15 + commit Dockerfile/docs/demo-tools-sans-secrets | ~3–4 days | Repo pushed + CI green on both lanes; a signed release APK walks the full flow on a real device; no secret in repo or URL |
| **P1 — Field truth & robustness** | Screens §2.1–2.8; C3–C7, H1, H4–H8, M2, M4, M7, M12 | ~3 wks | A fresh phone enrolls in-app and captures a batch where **every field-capturable criterion goes green**; kill-and-resume test passes; stuck sync visible & retryable |
| **P2 — Portal** | T3.4 read API, roles/auth (fix H14, M3, M5), dashboard/detail, lab QR flow, registry forms, issuance action | ~2–3 wks | Lab closes C7 by scanning a sample QR; admin issues a credit with an audit event; zero curl in the workflow |
| **P3 — Deploy & scale-hardening** | §4 all; H2, H3, M1, M6, C8b key-versioning | ~1–2 wks (overlaps P2) | Staging URL; real device syncs over TLS; restore drill done; 200-device smoke, zero 5xx |
| **P4 — Trust switches & polish** | Attestation creds+flip, v2-required flip, transport factors (Rainbow-gated), H15 plausibility, checklist hub, full Hindi i18n, M8 policy, M11/M13/M14 | ongoing | External items land behind flags; grandmother-test with real operators |
| **P5 — Platform** | Europe/Pro skin, white-label, multi-tenant, iOS (M9) | later | Second tenant/brand ships without touching screens |

**Process discipline (unchanged, now CI-enforced):** one task = one commit = one green gate; additive-only API/schema; config read live from env; compliance only via the provisional model; credit-math changes only with methodology sign-off behind flags.

---

## 8. Definition of production-ready

A fresh phone **enrolls via QR** against a **TLS'd cloud backend**; an operator captures a batch where **every field criterion turns green** and can **see and retry** anything stuck; a lab closes C7 by **scanning the physical sample's QR**; an admin presses **"Issue"** leaving an immutable audit trail; crashes reach Sentry; the fleet runs **signed, obfuscated, 16 KB-clean release builds**; and **no single machine dying loses one byte of evidence or one line of code.**
