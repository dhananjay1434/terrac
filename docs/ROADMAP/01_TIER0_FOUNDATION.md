# Tier 0 — Foundation: "Survivable & Verifiable MVP"

> **Benchmark when this tier is green:** the project can no longer be destroyed by one laptop dying; every commit is verified by CI on a clean machine; `pip install -r requirements.txt` + documented env vars boots the server on a fresh host; a release APK is signed with a real key. **This is the minimum bar to call anything an MVP.**
>
> **Total effort: ~1 day.** Nothing here needs methodology sign-off or external parties. Do this tier first, in order.

---

## T0.1 — Create a remote and push everything ⚠️ HIGHEST PRIORITY IN THE ENTIRE ROADMAP

- **Where:** git config (no code change).
- **Why:** `git remote -v` is empty. 15 commits of security/compliance work exist only in `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`. A disk failure erases the project.
- **What:**
  1. Create a private repo (GitHub/GitLab), e.g. `dmrv`.
  2. ```bash
     git remote add origin git@github.com:<org>/dmrv.git
     git push -u origin remediation/phase-by-phase
     git push origin main
     ```
  3. In repo settings: protect `main` (require PR + passing checks once T0.4 lands); default branch = `main`.
- **Gate:** `git remote -v` shows origin; both branches visible in the web UI.
- **Effort:** S.

## T0.2 — Commit the in-flight P0.a work

- **Where:** uncommitted diff on `backend/server.py` (the `_load_env()` / `DMRV_DISABLE_DOTENV` guard + `_require_secret()` consolidation, server.py:81–98 and 170–184), `backend/tests/test_p0_21_hmac_secret.py`, `REMEDIATION_LOG.md` (+65 lines).
- **Why:** this change is what makes the suite fully green (262/0, the old p0_21 dotenv failure is fixed by it). It is done, tested, and sitting unstaged.
- **What:** `git add backend/server.py backend/tests/test_p0_21_hmac_secret.py REMEDIATION_LOG.md && git commit -m "fix(config): dotenv opt-out + single _require_secret choke point (P0.a)"`.
- **Gate:** `git status` clean for those files; `cd backend && python -m pytest -q` → 262/1/0.
- **Effort:** S.

## T0.3 — Track the docs that are the plan of record

- **Where:** 13 untracked files: `docs/REMEDIATION_PLAN_NONUI.md`, `docs/UX_BUILD_PLAN.md`, `docs/UX_DESIGN_PLAN.md`, `docs/UX_EXECUTION_PLAN.md`, `docs/UX_FIELD_THEME_SPEC.md`, this `docs/ROADMAP/` folder, `detailed.md`, plus the business docs (`CBAM_*`, `STRATEGIC_*`, `INSTITUTIONAL_*`, `KOLHAPUR_*`, `RAINBOW_MEETING_QUESTIONS.md`).
- **What:** commit engineering docs as-is. Move business/strategy docs to `docs/business/` in the same commit (they are not engineering docs — see T4.10 for full docs reorganization; the minimal move now prevents the sprawl growing).
- **Gate:** `git status --porcelain | grep '^??'` returns nothing you care about.
- **Effort:** S.

## T0.4 — Commit `backend-ci.yml` and make CI real

- **Where:** `.github/workflows/backend-ci.yml` (exists, 70 lines, **untracked — CI has never run**).
- **Why:** the file is already correct: blocking `pytest -q` job with `DMRV_DISABLE_DOTENV=1`, `DMRV_HMAC_SECRET=test-secret`, `DMRV_ADMIN_SECRET=test-admin-secret`, in-memory SQLite, `DMRV_SKIP_MIGRATIONS=1` (values must stay matched to `backend/tests/conftest.py` — several tests assert the exact literals); informational `ruff` job with `continue-on-error: true`.
- **What:** `git add .github/workflows/backend-ci.yml && git commit`. Push. Watch the first-ever CI run. Fix anything environment-specific it surfaces (expect none — env is self-contained).
- **Gate:** green check on the remote for the `tests` job.
- **Effort:** S. **Depends on:** T0.1, T0.5 (CI installs from requirements.txt, which is currently broken — do T0.5 first or in the same push).

## T0.5 — Fix requirements.txt (deploy-breaking)

- **Where:** `backend/requirements.txt` (13 lines).
- **Why:** `server.py:26` imports `from dotenv import load_dotenv` and `server.py:44-45` imports `cryptography.hazmat...Ed25519PublicKey` — **neither `python-dotenv` nor `cryptography` is declared.** They install today only as transitive luck. A clean host may not boot.
- **What:**
  1. Add to `requirements.txt`:
     ```
     cryptography==44.0.0
     python-dotenv==1.0.1
     ```
     (or current stable pins; pin exactly, matching the style of the file).
  2. Split test-only deps out: create `backend/requirements-dev.txt` containing `pytest==8.3.4`, `pytest-asyncio==0.25.2`, `ruff` and remove them from `requirements.txt`. Update `.github/workflows/backend-ci.yml` install step to `pip install -r requirements.txt -r requirements-dev.txt`.
- **Gate:** on a fresh venv: `pip install -r requirements.txt && python -c "import server"` (with the three required env vars set) succeeds; CI green.
- **Effort:** S.

## T0.6 — Real Android release signing (ship blocker)

- **Where:** `android/app/build.gradle.kts` — the release block currently reads:
  ```kotlin
  buildTypes {
      release {
          // TODO: Add your own signing config for the release build.
          // Signing with the debug keys for now, so `flutter run --release` works.
          signingConfig = signingConfigs.getByName("debug")
      }
  }
  ```
- **Why:** the debug keystore is public knowledge; any "release" APK built today can be repackaged/replaced. Also, freeRASP's `TALSEC_SIGNING_CERT_HASH` check is meaningless while the signing cert is the debug cert.
- **What:**
  1. Generate a keystore (store it OUTSIDE the repo, e.g. a password manager + CI secret):
     ```bash
     keytool -genkey -v -keystore dmrv-release.keystore -alias dmrv -keyalg RSA -keysize 4096 -validity 10000
     ```
  2. Create `android/key.properties` (gitignored — add `android/key.properties` to `.gitignore`):
     ```properties
     storePassword=***
     keyPassword=***
     keyAlias=dmrv
     storeFile=/absolute/path/dmrv-release.keystore
     ```
  3. In `build.gradle.kts`, above `android {}`: load the properties file; add
     ```kotlin
     signingConfigs {
         create("release") {
             keyAlias = keystoreProperties["keyAlias"] as String
             keyPassword = keystoreProperties["keyPassword"] as String
             storeFile = file(keystoreProperties["storeFile"] as String)
             storePassword = keystoreProperties["storePassword"] as String
         }
     }
     buildTypes { release { signingConfig = signingConfigs.getByName("release") } }
     ```
  4. Recompute the SHA-256 signing-cert hash and update the `TALSEC_SIGNING_CERT_HASH` dart-define used by freeRASP (`lib/services/device_integrity_service.dart`).
- **Gate:** `flutter build apk --release` succeeds; `apksigner verify --print-certs build/app/outputs/flutter-apk/app-release.apk` shows your cert, not `Android Debug`.
- **Effort:** M (mostly key ceremony + freeRASP hash update).

## T0.7 — Minimal Flutter CI lane

- **Where:** new file `.github/workflows/flutter-ci.yml` (the existing `codegen.yml` only guards Drift codegen drift).
- **What:**
  ```yaml
  name: flutter-ci
  on:
    push: { branches: [main, "remediation/**"] }
    pull_request:
  jobs:
    analyze-test:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: subosito/flutter-action@v2
          with: { channel: stable }
        - run: flutter pub get
        - run: flutter analyze          # currently 25 infos/warnings, 0 errors — passes
        - run: flutter test
  ```
  (Optional hardening later: `--fatal-infos` once T4.4 clears the 25 issues.)
- **Gate:** green run on the remote.
- **Effort:** S. **Depends on:** T0.1.

## T0.8 — Repo cruft sweep (one commit)

- **Where / What:**
  | Item | Action |
  |---|---|
  | `New folder.zip` (5.4 MB, repo root, gitignored but on disk) | delete from disk |
  | `backend/dummy.jpg` (5 bytes, **tracked**) | `git rm backend/dummy.jpg` (if a test needs a fixture image, it should create one in tmp — grep tests first: `grep -rn dummy.jpg backend/tests/`) |
  | `yarn.lock` (86 bytes, tracked, no JS in project) | `git rm yarn.lock` |
  | `dmrv_app.iml`, `android/dmrv_app_android.iml` (tracked IDE files) | `git rm --cached`, add `*.iml` to `.gitignore` |
  | `.gradio/` (on disk, not ignored) | add `.gradio/` to `.gitignore`, delete dir |
  | `.baseline_*.txt` (already ignored) | delete from disk once REMEDIATION_LOG references are archived |
  | `README.md` (one line: "# Here are your Instructions") | replace with a real 30-line README: what the project is, layout (backend / lib / docs), how to run backend (`.env.example` → `.env`, `pip install`, `uvicorn server:app`), how to run app (dart-defines list), link to `PROJECT_README.md`, `detailed.md`, `docs/ROADMAP/` |
- **Gate:** `git status` clean; `git ls-files | grep -E '\.iml|yarn.lock|dummy.jpg'` empty.
- **Effort:** S.

## T0.9 — Merge to main

- **What:** once T0.1–T0.8 are committed and CI is green, open a PR `remediation/phase-by-phase` → `main`, let both workflows run, merge. From now on, work in short-lived branches off `main` with PR review.
- **Gate:** `git log main -1` is no longer `3469c10 initial`.
- **Effort:** S.

---

## ✅ Tier 0 exit criteria (the benchmark, verbatim)

- [ ] Remote exists; both branches pushed; `main` protected and current.
- [ ] Working tree clean; all engineering docs tracked.
- [ ] Backend CI + Flutter CI green **on the remote** (first ever verified-on-clean-machine run).
- [ ] Fresh-host install works from requirements.txt alone.
- [ ] `apksigner` shows a non-debug release cert.
- [ ] No tracked IDE files / stray artifacts; README is real.

**You may now honestly call this a survivable, CI-verified MVP suitable for a supervised pilot.**
