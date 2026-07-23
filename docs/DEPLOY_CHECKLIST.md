# Deploy Checklist

What must be true before this system is actually running in production — not a demo, not a
local dev box. Each item names the exact config the code already enforces or expects; none
of this is aspirational, it's what `settings.py`/`db.py`/`main.dart` already check for or
silently depend on.

---

## Backend

### Required environment variables (the process refuses to boot without these)

- **`DATABASE_URL`** — `db.py` raises `RuntimeError` at import time if unset. Must point at
  a real hosted Postgres for production (`postgresql+asyncpg://...`); the codebase's own
  regression guarantee (SQLite in tests) is not a production target.
- **`DMRV_ADMIN_SECRET`** — `settings.py`'s `_require_secret` raises if unset. Gates every
  `X-Admin-Secret` ops endpoint (`routers/admin.py`, `routers/exports.py`).
- **`DMRV_HMAC_SECRET`** (or the versioned-key form, `DMRV_HMAC_ACTIVE_KEY` + numbered keys)
  — required for LCA signature verification (`lca_signature`); rotating it invalidates every
  previously-signed batch's verifiability, so rotate deliberately, not casually.

### Recommended / conditionally required

- **`DMRV_SENTRY_DSN`** (backend) — error tracking. Not boot-blocking today; still needed for
  production observability.
- Any `RegistryConfig`/`Project` rows a deployment intends to use — these are admin-created
  via the portal, not seeded automatically (see PR-4: a project with no `registry_config_id`
  gets the DEFAULT/grandfather behavior, not an error).

### Database

- [ ] Real hosted Postgres provisioned, `DATABASE_URL` pointed at it.
- [ ] `alembic upgrade head` run against it (every migration in this repo is additive —
      confirm `alembic heads` shows exactly one head before deploying).
- [ ] Backup/restore policy in place — this is the system of record for issued credits
      (PR-1's `CreditIssuance` ledger); losing it loses issuance history.

### Compliance/capture gates — which to enable per environment

| Gate | Env var | Recommended for prod | Why |
|---|---|---|---|
| Compliance C0-C10 | `COMPLIANCE_ENFORCED` (module constant, not currently an env override) | ON (already default) | Data-integrity backstop — see corroboration.py. |
| Attestation | `DMRV_ATTESTATION_ENFORCED` | Per fleet's device-integrity posture | Grace-window protects pre-existing enrolled devices. |
| Parcel overlap | `DMRV_PARCEL_OVERLAP_ENFORCED` (see settings.py) | ON | Anti-double-counting across projects. |
| Day-start lock | `DMRV_DAYSTART_LOCK` (app dart-define) | Elect deliberately per fleet | UX-blocking; R6/PR-5's own scope note. |
| Blur rejection | `DMRV_BLUR_GATE_ENFORCED` (app dart-define) | **OFF until field-calibrated** | See `docs/CAPTURE_GATE_ROLLOUT.md` — do not flip blind. |
| Geofence warning | `DMRV_GEOFENCE_CAPTURE` (app dart-define) | **OFF until field-calibrated** | Same rollout doc. |
| Device parcel geometry | `DMRV_DEVICE_PARCEL_GEOMETRY` (backend) | Elect deliberately | Needed before geofence capture is useful at all. |

---

## App (Flutter)

### Required dart-defines for a release build

- **`SENTRY_DSN`** — `main.dart`'s `validateReleaseConfig` **throws and refuses to run** a
  release build (`kReleaseMode == true`) with an empty DSN. This is enforced in code, not
  just documented — a release build without it will not boot.
- **`DMRV_API_BASE_URL`** — fallback base URL (`api_base.dart`); the enrolled secure-storage
  value takes priority at runtime, but CI/first-run builds should still set this so a fresh
  install has a sane default before enrollment.

### Android release signing

- [ ] Real release keystore configured (not the debug key) — `android/` signing config
      pointed at it, keystore + passwords held outside the repo (secret manager / CI secrets,
      never committed — see `docs/SECRET_ROTATION.md` for the git-hygiene half of this).
- [ ] `flutter build apk --release` (or `appbundle`) produces a signed artifact; verify with
      `apksigner verify`.

### iOS release signing

- Follow `docs/IOS_BUILD_RUNBOOK.md` in full — as of that runbook's own last note, the iOS
  build is **documented but unverified on a macOS host** (this repo's dev host is Windows).
  Do not consider iOS deploy-ready until someone actually runs it on macOS and the runbook's
  per-plugin smoke-test table is confirmed, not just read.

### TLS trust

- [ ] Backend served over HTTPS with a valid certificate (not self-signed) for any
      production `DMRV_API_BASE_URL`.
- [ ] If certificate pinning is enabled anywhere in the app's HTTP client config, confirm the
      pinned certificate/public key matches the actual production certificate BEFORE
      shipping a release build — a pinning mismatch bricks every device's connectivity at
      once, with no server-side fix available.

---

## Portal (web frontend)

- [ ] `npm run build` produces a production bundle; `npx tsc --noEmit` clean.
- [ ] Portal's API base URL points at the production backend, not localhost.
- [ ] Portal login is served over HTTPS (session tokens must never travel over plaintext
      HTTP).

---

## Final pre-launch gate

Confirm ALL of the following are true, not just built:

- [ ] `alembic upgrade head` has actually run against the production database.
- [ ] At least one `PortalUser` with role `admin` exists in production (there is no seed —
      see `docs/PATH_TO_ISSUANCE.md` if this is the first deploy).
- [ ] A real device has enrolled against the production backend end-to-end (register →
      capture → sync → portal review) — not just against a local/dev backend.
- [ ] `docs/SECRET_ROTATION.md`'s current-state check has been re-run against THIS
      deployment's actual secret values, not assumed clean from a prior review.
