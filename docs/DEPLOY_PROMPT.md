# DEPLOY PROMPT — dMRV demo stack (Render + Netlify + Android phone)

> Copy everything below the line into the agent. It assumes: this repo checked
> out at the paths shown, `git` `node/npm` `flutter` `adb` `curl` installed, a
> GitHub account that can push this repo, a Render account, and a Netlify
> account. The agent must follow steps IN ORDER and STOP when a check fails.

---

You are deploying a 3-part system. Follow every step exactly, in order. Do not
skip steps. Do not improvise. After each **CHECK**, compare the output to the
expected value: if it matches, continue; if it does not match, STOP and report
the step number and the exact output you saw.

Write down these three values as you obtain them (you will substitute them
wherever you see the placeholder):

- `<RENDER_URL>`   — the backend URL, e.g. `https://dmrv-api.onrender.com` (no trailing slash)
- `<PORTAL_URL>`   — the portal URL, e.g. `https://dmrv-portal.netlify.app` (no trailing slash)
- `<ADMIN_SECRET>` — the value of `DMRV_ADMIN_SECRET` from the Render dashboard

The repo root on this machine is:
`c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`
Run all commands from a Git-Bash shell in that directory unless told otherwise.

## STEP 0 — Push the repo to GitHub

Render builds from GitHub, so everything must be committed and pushed first.

```bash
git add -A
git commit -m "chore: pre-deploy snapshot" || echo "nothing to commit"
git push origin feature/t5-india
```

**CHECK 0:** `git status` prints `nothing to commit, working tree clean` and
the push shows no errors.

## STEP 1 — Deploy the backend on Render (Blueprint)

1. Open https://dashboard.render.com in a browser. Log in.
2. Click **New +** → **Blueprint**.
3. Connect the GitHub repository `dhananjay1434/terra` (grant access if asked).
4. When asked for a branch, choose **`feature/t5-india`**.
5. Render reads `render.yaml` from the repo root. It will show two resources:
   a web service **dmrv-api** and a database **dmrv-db**. It will PROMPT for
   one env var it cannot generate: **`DMRV_ALLOWED_ORIGIN`** — type the
   placeholder `https://example.invalid` for now (you will replace it in
   STEP 3 after the portal exists).
6. Click **Apply / Deploy** and wait. First build takes 5–10 minutes.
7. When the service shows **Live**, copy its URL from the top of the service
   page. That is `<RENDER_URL>`. Also open the service's **Environment** tab
   and copy the generated value of `DMRV_ADMIN_SECRET` — that is
   `<ADMIN_SECRET>`.

**CHECK 1:** run (replace the placeholder):

```bash
curl -s <RENDER_URL>/api/health
```

Expected output exactly: `{"status":"ok","db":"ok"}`
(If the service idled, the first request can take ~60 s — free tier cold
start. Retry once after 60 s before declaring failure.)

## STEP 2 — Deploy the portal on Netlify

```bash
cd portal
npm ci
VITE_API_BASE=<RENDER_URL> npm run build
```

**CHECK 2a:** the build ends with `✓ built in …` and a `dist/` folder exists
(`ls dist/index.html` prints the path, no error).

Now deploy the `dist/` folder. Use the Netlify CLI (option A) or the web UI
(option B) — either is fine.

- **Option A (CLI):**
  ```bash
  npx netlify-cli deploy --prod --dir=dist
  ```
  Log in when the browser opens; accept "create & configure a new site".
  The command prints a `Website URL` at the end — that is `<PORTAL_URL>`.

- **Option B (web UI):** open https://app.netlify.com/drop and drag the
  `portal/dist` folder onto the page. The resulting site URL is `<PORTAL_URL>`.

The SPA redirect file (`portal/public/_redirects`) is already included in the
build, so page reloads on deep links will work.

**CHECK 2b:** open `<PORTAL_URL>` in a browser. A login page renders (it will
not accept logins yet — CORS is still closed; that is expected).

## STEP 3 — Point the backend's CORS at the portal

1. In the Render dashboard, open the **dmrv-api** service → **Environment**.
2. Edit `DMRV_ALLOWED_ORIGIN` and set it to `<PORTAL_URL>` exactly — https,
   no trailing slash, no path.
3. Save. Render redeploys automatically (2–3 minutes).

**CHECK 3:** `curl -s <RENDER_URL>/api/health` again returns
`{"status":"ok","db":"ok"}` after the redeploy finishes.

## STEP 4 — Create the portal admin user

The portal has no self-signup (by design). Create the admin from this machine,
pointed at Render's database.

1. In the Render dashboard open the **dmrv-db** database page and copy the
   **External Database URL** (starts with `postgresql://`).
2. Run (replace both placeholders; pick any strong password and remember it):

```bash
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/backend"
pip install -r requirements.txt
export DATABASE_URL='<EXTERNAL_DATABASE_URL>'
export DMRV_DISABLE_DOTENV=1
export DMRV_HMAC_SECRET=bootstrap-not-used DMRV_ADMIN_SECRET=bootstrap-not-used DMRV_ALLOW_WEAK_SECRETS=1
export DMRV_PORTAL_PASSWORD='<CHOOSE_A_PASSWORD>'
python create_portal_user.py --email admin@demo.org --role admin
```

**CHECK 4:** the script prints `portal user created: admin@demo.org (admin)`.
Then open `<PORTAL_URL>`, log in with `admin@demo.org` + the password. The
dashboard loads.

## STEP 5 — Mint a device enrollment token

```bash
curl -s -X POST <RENDER_URL>/api/v1/admin/mint-token \
  -H "X-Admin-Secret: <ADMIN_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"token":"demo-token-001","expires_in_days":30}'
```

**CHECK 5:** output contains `"status":"minted"` and `"token":"demo-token-001"`.
(A 409 `token_already_exists` is also fine — the token is already usable.)

## STEP 6 — Build and install the Android app

Use a DEBUG build: it uses the system TLS trust store (works with Render's
certificate automatically) and needs no signing keystore or Sentry DSN.

1. Enable **Developer options → USB debugging** on the Android phone and plug
   it into this machine via USB. Accept the "allow USB debugging" prompt on
   the phone.

```bash
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv"
flutter build apk --debug --dart-define=DMRV_API_BASE_URL=<RENDER_URL>
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

**CHECK 6:** `adb install` prints `Success`, and the app "dmrv_app" appears on
the phone.
(No phone cable? Copy `build/app/outputs/flutter-apk/app-debug.apk` to the
phone by any means and tap it to install, allowing "install unknown apps".)

## STEP 7 — End-to-end demo verification

1. Open the app on the phone. On the enrollment screen enter:
   - Server URL: `<RENDER_URL>`
   - Enrollment token: `demo-token-001`
   and tap ENROLL.
   **CHECK 7a:** the app reports successful enrollment (no red error).
2. In the app, create a demo batch (follow the dashboard flow: batch →
   moisture readings → burn/telemetry → yield → application) and let it sync
   (the sync banner turns to "ALL DATA SECURE" when the outbox is empty).
   **CHECK 7b:** no sync errors shown.
3. Open `<PORTAL_URL>`, log in as `admin@demo.org`.
   **CHECK 7c:** the batch created from the phone is visible, with its
   evidence and a PROVISIONAL credit state (provisional is CORRECT — a batch
   only leaves provisional when every corroborating input, including lab
   results, is present).

If checks 7a–7c pass, the demo stack is fully deployed. Report the three URLs
and stop.

## Known demo-tier limitations (do not "fix" these)

- Render free tier cold-starts after ~15 min idle (first request ~60 s) and
  the free Postgres expires after 30 days.
- Uploaded photos live on the container's ephemeral disk (`DMRV_MEDIA_BACKEND`
  defaults to `local`): they survive requests but are lost on redeploy. Batch
  data itself is in Postgres and survives.
- The debug APK is for the demo only — release builds have separate signing +
  TLS-pinning requirements (see docs/RELEASE_CHECKLIST.md).
