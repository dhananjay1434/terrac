# Status Report — Android readiness, white-label, videos, and pilot-readiness

Grounded in the actual code as of 2026-07-24. Answers four questions: (1) is the Android app
buildable/ready, (2) is one week enough for a white-label reskin, (3) what's missing, (4) can we
run a pilot — with the specific, verified truth about video evidence in the portal.

---

## 1. Android — yes, it builds and runs today

- A **debug APK builds cleanly** (verified twice this cycle: `build/app/outputs/flutter-apk/app-debug.apk`,
  universal/all-ABIs so it installs on cheap 32-bit phones too). `flutter analyze` is clean; all
  405 Flutter tests pass.
- **Demo mode works** (`DMRV_DEMO_MODE=true`): thermocouple, weight scale, GPS, and RASP are all
  simulated — no hardware needed to show the full flow.
- **For a real release build** you need two standard things (not blockers, just not done yet):
  1. **Release signing** — a real keystore + signing config (currently only the debug key exists).
  2. **`SENTRY_DSN`** — `main.dart` deliberately refuses to build a release without it (crash
     reporting must be on in production). Pass it as a `--dart-define`.
- iOS: **unverified on a macOS host** (dev machine is Windows) — see `docs/IOS_BUILD_RUNBOOK.md`.
  Don't promise iOS until someone actually runs that runbook.

**Verdict:** Android is buildable and demo-ready now; a signed release build is a half-day of
standard setup.

---

## 2. White-label in one week — yes for theme + brand; scope the "small things" carefully

The theming is **centralized**, which is what makes a reskin fast:
- **App colors/typography:** one file — `lib/ui/design/tokens.dart` — a `DmrvTokens` class with
  semantic tokens (`surface`, `accent`, `textPrimary`, `success`, …). Swap the values → the whole
  app reskins. This is the right architecture for white-labeling.
- **Portal colors:** CSS custom properties (`var(--…)`) — also centralized.

What a per-client white-label actually involves (all mechanical, ~days not weeks):
- **Brand name:** "TerraCipher" is hard-coded in ~21 spots (app title + `TerraCipherApp` class in
  `main.dart`, dashboard wordmark, portal sidebar/topbar/page `<title>`s). Today it's a
  find-replace; ideally extract to a single constant during the first white-label so future ones
  are one line.
- **Logo / app icon / splash:** standard Flutter asset swap.
- **Android package id / iOS bundle id** (e.g. `com.client.app`): a client-branded store listing
  or APK needs this — moderate config change (also affects the RASP `signingCertHashes`).
- **Colors + fonts:** `tokens.dart` + portal CSS vars.

**Verdict:** a **visual + brand white-label is comfortably doable in one week** — the theme system
is built for it. The risk in "one week" is the *undefined* "small small things": if those include
feature changes, new integrations, or fixing the gaps in §3/§4, budget those separately. Pure
reskin+rebrand: days.

---

## 3. Videos in the portal — ⚠️ captured & stored, but NOT viewable (real gap)

This is the one that would embarrass us in front of an auditor, so being precise:

- **The app captures video** — quench video + density-test video (PR-6) and the day-start
  walkthrough video (PR-5) — uploads them through the same signed `/media` rail, and the backend
  **stores + SHA-256-verifies** them exactly like photos. The capture side is fully integrated.
- **The portal cannot play them.** `EvidenceGallery.tsx` and `EvidenceLightbox.tsx` render every
  media item with an **`<img>` tag only** — there is no `<video>` player. A video item lands in
  `<img src=…>`, fails to decode, and shows the **"Preview unavailable"** fallback. (The one
  `<video>` in the codebase, `LabScan.tsx`, is the live QR-scanner camera, not evidence playback.)
- The media-streaming endpoint (`portal/routes.py::/media/{operation_id}`) also serves everything
  as `application/octet-stream`, not the real mime type.

**Net:** the whole *point* of requiring quench/density video (stronger, harder-to-fake evidence) is
currently undercut on the verifier side — a VVB/manager can't watch them. **This is not
integrated end-to-end.**

**Fix (small, well-scoped):**
1. Backend: serve the correct `media_type` by extension/capture_type (`video/mp4` for videos).
2. Portal: in `EvidenceGallery`/`EvidenceLightbox`, branch on capture_type (or mime) — render
   `<video controls>` for videos, `<img>` for photos.
   Estimate: ~1 day incl. tests. Should be done before any pilot that captures video.

---

## 4. What's missing — consolidated, split by "pilot-blocker" vs "later"

### Pilot-blockers (fix before real, unattended field use)
- **Burn-telemetry durability (Tier-1 #1):** the entire burn's temperature curve lives in RAM
  until `endBurn` — an OOM-kill / dead battery / crash mid-burn on a cheap phone loses the whole
  burn's core evidence. Design already written: `docs/BURN_TELEMETRY_RESILIENCE_DESIGN.md`. This is
  the #1 field risk.
- **Video playback in portal (§3)** — captured but unviewable.
- **Sustained heat/battery (Tier-1 #2/#3):** whole-screen rebuild per BLE sample for the whole
  burn; GPS `high` on every capture. Both in the same design doc.

### Needed for a *hosted* pilot (vs LAN demo)
- **Object storage (S3/MinIO) for media** — the hosted Render backend has no persistent media
  store; photos/videos captured in the field won't survive/serve without it. (The `S3MediaStorage`
  backend exists in `storage.py`; it just needs a bucket + creds wired.)
- **Release signing pipeline + `SENTRY_DSN`** (§1).
- **Secrets rotation** per `docs/DEPLOY_CHECKLIST.md`.

### Not pilot-blocking — required only for *real credit issuance*
- **Methodology-conformance sign-off (PR-C1)** and **Rainbow numeric annexes (PR-C2)** — external
  VVB/process work; a pilot can capture and grade evidence without issuing real credits yet.

### Cosmetic / demo-only
- 3 demo evidence images still missing (lab certificate, soil application, dispatch truck) — the
  image generator hit a rate limit; only 5 of 8 were made. Purely demo polish.

---

## 5. Can we run a pilot with our app?

Depends on which kind — three honest tiers:

- **Attended / shadow pilot** (our people present, short controlled burns, or capture-only with
  paper backup): **yes, soon** — after the video-playback fix (§3) and ideally the burn-telemetry
  durability fix, both small/scoped. This proves the capture→sync→verify loop with a real operator.
- **Unattended real-field pilot** (operators alone, multi-hour burns, their own cheap phones):
  **not yet** — the Tier-1 durability fix is mandatory first; losing a 3-hour burn's telemetry to
  an OOM-kill would burn trust with the very partner you're piloting with.
- **Issuing real credits from the pilot:** **no** — gated on PR-C1 conformance sign-off. Frame the
  pilot as "generate audit-grade, cryptographically-verified evidence records," not "mint credits."

**Bottom line:** the app is Android-ready and white-label-ready; the two things standing between
"impressive demo" and "trustworthy pilot" are small and known — **portal video playback** (~1 day)
and **burn-telemetry durability** (design done, ~medium). Do those two and an attended pilot is on
the table.
