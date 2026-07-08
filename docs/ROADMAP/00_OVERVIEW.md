# dMRV Roadmap — From Today's Code to the Best Version of Itself

**Created:** 2026-07-07 · **Source:** `detailed.md` (full audit, repo root) · **Branch:** `remediation/phase-by-phase`

This folder is the execution plan for everything the audit found. Nothing here has to be done *now* — the point is that when you decide to do it, the exact file, line, change, and proof-of-done are already written down, and you always know **what level the codebase is at**.

---

## How this folder works

| File | Tier | Benchmark you reach when the tier is 100% green |
|---|---|---|
| [01_TIER0_FOUNDATION.md](01_TIER0_FOUNDATION.md) | **T0 — Foundation** | *"Survivable & verifiable MVP"* — the repo can't be lost, CI actually runs, a stranger can install and boot the backend from scratch, and a release APK is genuinely signed. |
| [02_TIER1_RAINBOW.md](02_TIER1_RAINBOW.md) | **T1 — Rainbow-Compliant** | *"Methodology-complete dMRV"* — every reason in the C10 compliance catalog is reachable; no dormant gates, no hardcoded bypasses; ~62% → ~100% criteria enforcement (minus items blocked on Rainbow themselves, which become explicit, inert, documented switches). |
| [03_TIER2_SECURITY.md](03_TIER2_SECURITY.md) | **T2 — Adversary-Ready** | *"Verifier-defensible security"* — a rooted phone, a replayed request, a brute-forced admin header, or a decompiled APK no longer moves a carbon credit. |
| [04_TIER3_PRODUCTION.md](04_TIER3_PRODUCTION.md) | **T3 — Production Operations** | *"Deployable, observable, recoverable"* — one-command deploy on Postgres + object storage, metrics/logs/health you can page on, tested backups, and a read API so operations doesn't need DB access. |
| [05_TIER4_POLISH.md](05_TIER4_POLISH.md) | **T4 — Polished Final** | *"Best version of itself"* — refactored modules, e2e/golden test coverage, third locale, field analytics, spotless docs and repo. |
| [06_TIER5_UI_PLATFORM.md](06_TIER5_UI_PLATFORM.md) | **T5 — UI & Platform** | *"One codebase, any brand, any market"* — the dark/light UI seams unified into one token-driven design system; two first-class skins (Field/India + Pro/Global-EU); white-label in <1 day; multi-tenant SaaS backend. |
| [UI_CONSISTENCY_AUDIT.md](UI_CONSISTENCY_AUDIT.md) | — | The evidence paper for T5: every UI seam, inconsistency, and hardcoded style, file:line (findings U1–U12). |
| [TASKBOARD.md](TASKBOARD.md) | — | One-line checklist of every task ID for tracking. |

**Dependency rule:** tiers are ordered by *value-at-risk*, not difficulty. T0 before everything (it protects the work itself). T1 and T2 can interleave. T3 before real users. T4 whenever. T5 Stage A (UI unification) can start any time and should land before T4's golden tests; T5 Stages C/D (white-label/SaaS) want T1.1 and T3.4 first.

**Task ID convention:** `T<tier>.<n>` — e.g. `T1.2`. Every task has: **Where** (file:line), **What** (exact change, code included where it matters), **Gate** (the test/command that proves it's done), **Effort** (S <1h, M <1d, L 1–3d, XL >3d), **Blocked-by** (external dependency, if any).

---

## Load-bearing rules (violate these and you break the shipped client — carried from the Rainbow build protocol)

1. **Additive & backward-compatible only.** New tables, new *nullable* columns, new endpoints, new *optional* Pydantic fields. Never rename/drop/make-required an existing field. Deployed field devices sync against this API.
2. **Compliance is enforced only through the PROVISIONAL model.** Never reject an upload for a methodology reason. One mechanism: a pure `derive_*` function in `backend/corroboration.py` → a reason string → `assemble(extra_reasons=[...])` → persisted by `recompute_batch_credit` ([server.py:718-973](../../backend/server.py#L718)). Do not invent a parallel gate.
3. **Lab/`[V]` data is authoritative → admin-authenticated** (`X-Admin-Secret` + `hmac.compare_digest` + range-check, like `ingest_lab_hcorg`). Never device-asserted.
4. **Kiln-type-conditional rules stay inert** unless `kiln_type` is explicitly `'open'`/`'closed'`.
5. **Credit-math changes need methodology sign-off** and land behind an explicit module flag (the `TRANSPORT_EVENTS_ENFORCED` pattern) — never silently.
6. **One task = one commit = one green gate.** Backend gate: `cd backend && python -m pytest -q` (current baseline: **262 passed, 1 skipped, 0 failed**). Client gate: `flutter analyze` (25 issues, 0 errors — don't add any) + `flutter test` (151 passed, 2 skipped).
7. **Client schema changes** follow the build loop: edit `lib/data/local/tables.dart` → bump `AppDatabase.schemaVersion` by exactly 1 (`lib/data/local/app_database.dart`, one `if (from < N)` block, addColumn/createTable only) → `dart run build_runner build --delete-conflicting-outputs` → matching optional server field + reversible Alembic migration.
8. **Alembic chain:** current head is `e1f2a3b4c5d6` (annual_verifications). Every new migration sets `down_revision` to the current head at the time you write it, and must have a working `downgrade()`.

---

## Current verified state (baseline for all benchmarks)

- Backend: FastAPI, 21 endpoints, `server.py` 2,073 lines; pytest **262/1/0** (includes the still-uncommitted P0.a dotenv fix).
- Client: Flutter, Drift+SQLCipher schema **v22**, Ed25519 signing, cert pinning, FreeRASP; tests **151/2/0**.
- Rainbow: 8 of 15 core criteria enforced; 3 dormant (scale calibration, annual methane, PAH); C6 transport audit-only with uncited factors; several capture-only items. See the matrix in `detailed.md` §2.
- Ops: **no git remote, CI never executed, no Dockerfile, local-disk uploads, no metrics/structured logs, no read API.**
- Release: Android release builds signed with the **debug** keystore; no R8/ProGuard.
- UI: **two coexisting design systems** — the batch flow flips dark (FarmerTheme) / light (AppTheme) five times; 61 hardcoded color literals; only 2/9 screens localized; brand strings baked into screens. Single-tenant, single-brand. Full evidence: [UI_CONSISTENCY_AUDIT.md](UI_CONSISTENCY_AUDIT.md).

## Benchmark ladder at a glance

```
TODAY            T0 done          T1 done            T2 done             T3 done              T4 done             T5 done
  │                │                 │                  │                   │                    │                   │
  ▼                ▼                 ▼                  ▼                   ▼                    ▼                   ▼
"one laptop,   "survivable,     "Rainbow          "adversary-ready:   "production:         "best version:      "platform:
 62% gates,     CI-verified,     methodology-      attestation,        Postgres, S3,        modular, e2e-       one design system,
 debug-signed,  installable      complete —        rate limits,        metrics, backups,    tested, 3 locales,  2 skins (Field/Pro),
 UI split       MVP"             verifier can      no replay,          read API, one-       analytics,          white-label <1 day,
 dark/light"                     audit every       hardened APK"       command deploy"      spotless docs"      multi-tenant SaaS"
                                 criterion"
Suitable for:  supervised       Rainbow pilot     unsupervised        real buyers,         registry-grade      sellable 3 ways: own
 demo only      pilot            + verifier        field fleet         paying customers     flagship product    app / partner labels /
                                 review                                                                         SaaS orgs
```
