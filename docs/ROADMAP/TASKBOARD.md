# Task Board — every task, one line each

Tick boxes as tasks merge. Effort: S <1h · M <1d · L 1–3d · XL >3d. ⛔ = blocked on an external party (buildable/testable inert meanwhile).

## T0 — Foundation → *"Survivable & verifiable MVP"* (~1 day)

- [ ] **T0.1** (S) Create git remote, push both branches, protect `main` — **do first, everything is on one laptop**
- [ ] **T0.2** (S) Commit the in-flight P0.a dotenv/`_require_secret` work (server.py + test_p0_21 + log)
- [ ] **T0.3** (S) Commit the 13 untracked docs; move business docs to `docs/business/`
- [ ] **T0.4** (S) Commit `.github/workflows/backend-ci.yml` → first-ever CI run
- [ ] **T0.5** (S) Add `cryptography` + `python-dotenv` to requirements.txt; split requirements-dev.txt
- [ ] **T0.6** (M) Real Android release keystore (kill debug signing); update Talsec cert hash
- [ ] **T0.7** (S) Flutter CI lane (analyze + test)
- [ ] **T0.8** (S) Cruft sweep: zip, dummy.jpg, yarn.lock, *.iml, .gradio/, real README
- [ ] **T0.9** (S) PR → merge to `main`; branch-per-task from now on

## T1 — Rainbow Compliance → *"Methodology-complete dMRV"* (~1–1.5 wk) · ▶ executable handoff: [prompts/T1_EXECUTION_PROMPT.md](prompts/T1_EXECUTION_PROMPT.md)

- [ ] **T1.1** (L) Batch→project/scale linkage: nullable cols + migration + optional API fields + client schema v23 + `DMRV_PROJECT_ID` dart-define
- [ ] **T1.2** (M) Wire `scale_calibration_expired` gate (deriver exists, never called)
- [ ] **T1.3** (M) Wire `missing_annual_methane` gate (deriver exists, never called)
- [ ] **T1.4** (S) Remove hardcoded `enforced=False` PAH bypass (server.py:892)
- [ ] **T1.5** (M) ⛔ Cited fuel factors → flip `TRANSPORT_EVENTS_ENFORCED` → wire into LCA (do the asyncio-mark test cleanup now)
- [ ] **T1.6** (M) ⛔ Measured methane rate → LCA Step-7 CH4 penalty
- [ ] **T1.7** (M) ⛔ Conversion factor → C1 yield cross-check (`biomass_conversion_mismatch`)
- [ ] **T1.8** (L) `projects` table + admin endpoint + 1000-yr pathway election + inertinite completeness gate
- [ ] **T1.9** (S) Enforce ≥3 lab biochar-moisture samples on `/admin/lab`
- [ ] **T1.10** (S) Compliance report: per-check `enforcement` provenance field

## T2 — Security → *"Adversary-ready, verifier-defensible"* (~1.5–2 wk) · ▶ executable handoff: [prompts/T2_EXECUTION_PROMPT.md](prompts/T2_EXECUTION_PROMPT.md)

- [ ] **T2.1** (XL) ⛔ Server-side Play Integrity / DeviceCheck verification + nonce binding → flip `_ATTESTATION_ENFORCED`
- [ ] **T2.2** (M) Rate limiting (register/admin/media/evidence tiers, env-tunable)
- [ ] **T2.3** (M/L) Replay protection: v2 canonical with signed timestamp, staged client rollout
- [ ] **T2.4** (M) R8/ProGuard + `--obfuscate --split-debug-info`; archive symbols
- [ ] **T2.5** (S) `FLAG_SECURE` screenshots/recents (release builds); iOS snapshot blur
- [ ] **T2.6** (S/M) Truthful `/api/health` (DB probe) + secret entropy/length floor
- [ ] **T2.7** (S) EXIF/GPS trust-model honesty pass; plausibility signals into audit JSON
- [ ] **T2.8** (S) Rotate dev HMAC/admin secrets at first deploy; decide historical-signature policy

## T3 — Production Ops → *"Deployable, observable, recoverable"* (~2 wk)

- [ ] **T3.1** (M/L) Postgres CI lane with real migrations + `alembic check` + pool tuning
- [ ] **T3.2** (M) Real Dockerfile + compose + image-boot smoke test in CI
- [ ] **T3.3** (L) Object storage (S3/MinIO) for evidence media, versioned + object-lock; migrate pilot uploads
- [ ] **T3.4** (L) Admin read API: batch list (cursor pagination), batch detail, devices, summary
- [ ] **T3.5** (L) JSON logs + request IDs + `/metrics` + server Sentry + alert seeds
- [ ] **T3.6** (M) Nightly backups **with a tested restore drill**; document RPO/RTO
- [ ] **T3.7** (L) Async/debounced recompute — only after metrics prove the need
- [ ] **T3.8** (M) Load smoke test (200 devices); record baselines
- [ ] **T3.9** (M–L) Pick host, TLS, pin-rotation policy, platform secret manager

## T4 — Polish → *"Best version of itself"* (~2–3 wk, parallelizable)

- [ ] **T4.1** (L) Split server.py → schemas/auth/routes/credit modules (<700 lines left)
- [ ] **T4.2** (S/M) Named constants for all magic numbers; standardize response envelope
- [ ] **T4.3** (M) Tombstone correction workflow for moisture/composite/transport
- [ ] **T4.4** (M) Clear all 25 analyzer issues + ruff-clean backend; make both linters blocking
- [ ] **T4.5** (XL) E2E flow test + widget tests ×9 screens + goldens; ≥70% services/data coverage
- [ ] **T4.6** (L) Marathi locale + full string externalization (10 keys → full coverage, en/hi/mr parity test)
- [ ] **T4.7** (M) First-party field telemetry (sync/capture/BLE failure counters) + summary surfacing
- [ ] **T4.8** (L) ⛔ iOS release lane (signing, TestFlight) — or explicitly de-scope
- [ ] **T4.9** (M) Tag-driven release pipeline (signed artifact + changelog, hands-free)
- [ ] **T4.10** (M/L) Docs truth pass: DEPLOYMENT rewrite, PROJECT_README fix, docs reorg, ARCHITECTURE.md, CHANGELOG
- [ ] **T4.11** (S/M) DPDP data-handling note; buyer_contact log/Sentry redaction

## T5 — UI & Platform → *"One codebase, any brand, any market"* (~4–6 wk; evidence: [UI_CONSISTENCY_AUDIT.md](UI_CONSISTENCY_AUDIT.md))

**Stage A — Unify the UI (fixes U1–U12; start any time, land before T4.5 goldens)**
- [ ] **T5.1** (L) Semantic design-token layer (`DmrvTokens` ThemeExtension, field+pro instances, WCAG contrast unit test)
- [ ] **T5.2** (XL) Migrate all 9 screens + 3 widgets to tokens; end the dark/light flip (0 hex literals outside tokens.dart)
- [ ] **T5.3** (L) Merge `RuggedButton`+`PremiumFieldButton` → `DmrvButton`; panels → `DmrvPanel`; delete dead `PremiumActionCard`/`PremiumInputField`
- [ ] **T5.4** (M) One `DmrvErrorPanel`/`DmrvLoading`/`DmrvEmptyState`; fix armorSlate35 WCAG failure
- [ ] **T5.5** (L) Full string externalization (~10 → 60–120 ARB keys); brand strings out of screens (supersedes half of T4.6)
- [ ] **T5.6** (M) Navigation coherence: named routes; total freeze-forward back policy with `PopScope`

**Stage B — Dual skins**
- [ ] **T5.7** (M) Skin architecture: `DMRV_SKIN` dart-define / remote config → one-line theme switch; debug skin toggle
- [ ] **T5.8** (L) Design the Pro (Global/EU) skin as a real surface: calibrated tokens, locale-driven formats, SKINS.md
- [ ] **T5.9** (M) Golden matrix (9 screens × 2 skins × locales); both-skins-defined enforced structurally

**Stage C — White-label**
- [ ] **T5.10** (M) `Brand` config via `--dart-define-from-file`; `grep TerraCipher lib/` → 0
- [ ] **T5.11** (L) Android/iOS flavors per brand: own id, icon, label, keystore-per-brand
- [ ] **T5.12** (M) `scripts/new_whitelabel.sh` + WHITELABEL.md runbook; target <1 day per brand

**Stage D — Multi-tenant SaaS backend**
- [ ] **T5.13** (L) `organizations` table + nullable `org_id` on devices/projects/batches/tokens; org inherited from enrollment (server-derived)
- [ ] **T5.14** (XL) Per-org API keys, org-scoped reads with cross-tenant leak-test matrix, `GET /api/v1/app-config` remote branding, per-org storage prefixes
- [ ] **T5.15** (L) Per-tenant `MethodologyProfile` (thresholds as data, rules stay code; Rainbow = frozen default; profile hash in audit JSON)
- [ ] **T5.16** (L) Tenant lifecycle: provisioning, suspend, usage counters (billing meter), TENANCY.md, org data export

## External-dependency ledger (chase these in parallel — they gate the ⛔ tasks)

| Needed from | Item | Unblocks |
|---|---|---|
| Rainbow | Annex fuel-emission factors (with units) | T1.5 |
| Rainbow / methodology owner | Sign-off: measured CH4 substitution + GWP; conversion-factor tolerance; transport-penalty replacement rule; 1000-yr credit math | T1.5, T1.6, T1.7, T1.8 (math half) |
| Google | Play Console access + Play Integrity setup (needs release signing = T0.6) | T2.1 |
| Apple | Developer account (DeviceCheck/App Attest; also iOS lane) | T2.1, T4.8 |

## Benchmark ladder (what you can claim after each tier)

| After | You can honestly say |
|---|---|
| **T0** | "CI-verified MVP; installable from scratch; the work can't be lost; releases are genuinely signed." |
| **T1** | "Rainbow methodology-complete: every criterion enforced or explicitly awaiting Rainbow's own numbers — auditable per batch via the compliance endpoint." |
| **T2** | "Adversary-ready: rooted devices, replays, brute force, and decompilation don't move a credit." |
| **T3** | "Production service: one-command deploy, observable, recoverable, dashboard-ready." |
| **T4** | "Registry-grade flagship: modular, e2e-tested, tri-lingual, documented, hands-free releases." |
| **T5-A** | "One seamless UI: a single token-driven design system, no dark/light flips, no hardcoded styles." |
| **T5-B** | "Two markets, one codebase: Field (India) and Pro (Global/EU) skins switched by one flag." |
| **T5-C** | "White-label factory: any partner brand shipped in under a day without touching a screen file." |
| **T5-D** | "SaaS dMRV platform: isolated tenants with their own keys, branding, and methodology thresholds on one backend." |
