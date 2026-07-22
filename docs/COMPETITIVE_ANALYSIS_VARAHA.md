# Competitive Analysis — Varaha "Kalki" (com.varaha.biochar v1.6.2) vs. TerraCipher dMRV

Source: teardown of the shipped Varaha XAPK (`com.varaha.biochar_1.6.2`, Kotlin
Multiplatform / Compose, Play build 1006002) cross-referenced with our own
codebase (Flutter app + FastAPI backend + React verifier portal), all
code-verified this session.

## TL;DR — two different bets

- **Varaha = operational BREADTH.** A full field-operations platform for a
  multi-country, multi-program carbon company (biochar + ARR + regen). It runs
  the *whole supply chain*: farmer KYC + payments + legal consent, land/site
  mapping, excavation, biomass logistics, production cycles, biochar dispatch &
  distribution, facility admin — across India / Bangladesh / Kenya, shipping to
  real users today (v1.6.2, 16 DB migrations).
- **TerraCipher = verifiable MRV DEPTH.** A focused integrity pipeline:
  cryptographically-signed field evidence, sensor-grounded burn data (ESP32 BLE
  thermocouple), a transparent server-side CSI/Rainbow credit engine + compliance
  gates, and an auditor-facing **verifier portal**. Pre-production, but built for
  *defensibility of the carbon data*.

**Neither is strictly "better" — they optimized for different things.** Varaha
can run a supply chain today; we can *prove a credit is real* better. The
strategy is to close their breadth gap while keeping our integrity moat.

---

## Where VARAHA is ahead (what we're missing / lacking)

1. **Full farmer KYC & onboarding module** (`onboardlibrary`): identity docs
   (Aadhaar/Passport/NID, last-4 stored), **bank/payment capture** (account+IFSC,
   UPI, MFS/M-Pesa/bKash), finger-drawn **signature**, **FPIC legal consent**
   (country/language-specific PDF templates from CloudFront, signed + photo-of-
   farmer-holding-it). Ours is a text-only stub (name/phone/ID). **This is their
   biggest lead** — they own the entire farmer relationship + payout + legal.
2. **Logistics / supply chain**: biomass dispatch (truck, driver, weighbridge,
   truck-fill %, multi-site aggregation), biochar dispatch + distribution to
   farmers, shipment receiving with a Draft→In-Transit→Received state machine,
   facility intake re-weighing. We have end-use only, not the chain.
3. **Map boundary capture**: draw-polygon / GPS-walk / manual coords, WKT
   geometry, **overlap detection** + area-mismatch validation. We have none.
4. **ML Kit on-device vision**: **document scanner** (edge-detect + perspective
   correct for IDs/land docs/invoices), barcode, face detection. Directly
   relevant to the moisture-meter OCR idea — they already ship the doc-scan
   pipeline we'd need to adapt.
5. **On-device PDF generation** (PDFBox) for weight slips / site docs.
6. **Bulk-density testing** workflow (mass photo + video). We don't measure it.
7. **Enterprise multi-tenancy**: multi-role (Site/Facility Manager, Enumerator),
   multi-facility, multi-country field configs, multi-program (biochar/ARR/regen),
   tenant routing via a custom `x_header`.
8. **Media pipeline sophistication**: dedicated preprocess worker
   (compress/transcode), presigned-S3 upload with **live progress %**, a
   conversion-status state machine, and a cleanup worker. Our two-phase sync is
   solid but less elaborate on media conversion/progress.
9. **Product-ops maturity**: in-app updates, Remote-Config-driven "What's New",
   Firebase Remote Config **feature flags**, Crashlytics + Performance + A/B
   testing. We have Sentry only.
10. **iOS today** (KMP `ios_arm64` targets). We're Flutter (iOS-capable but
    Android-focused).
11. **Richer sync state machine**: 7 states incl. server-driven CONFLICT
    resolution and tombstone/delete; server_id write-back + media repointing.
12. **Shipping at scale**: v1.6.2 in production, 3 countries, real users. We're
    pre-production.

---

## Where WE are ahead (our moat / where we're the best)

1. **Encrypted database at rest (SQLCipher).** Our farmer/evidence data is
   encrypted. **Varaha's Room DB is PLAINTEXT SQLite** — their own shipped build
   stores farmer names, DOB, mobile, GPS, **drawn signatures, Aadhaar/passport
   refs, and bank account/IFSC/UPI/MFS payment IDs in the clear** (RE doc 07,
   MEDIUM finding). They collect *far more* sensitive PII than us and encrypt
   *none* of it. This is our single strongest, most demonstrable win.
2. **Per-submission cryptographic signing (Ed25519).** Every field submission is
   device-signed with server-side **replay protection** (signed-at window). Varaha
   uses standard **JWT bearer + refresh** — session auth, not evidence signing.
   Our evidence is cryptographically bound to a device at source; theirs isn't.
   For MRV *defensibility*, this is a category difference.
3. **Sensor-grounded burn evidence (ESP32 BLE thermocouple).** We capture live
   pyrolysis temperature telemetry from a hardware device with a **secure-element
   hardware attestation** path. Varaha's production cycle is **photo/video-stage
   only** — no live temperature sensor. We have physical burn-condition proof;
   they have pictures of a burn.
4. **Transparent, auditable credit engine + gates.** Our backend recomputes the
   CSI 8-step LCA, applies C0–C10 Rainbow compliance gates, and HMAC-signs the
   LCA audit. The credit math is inspectable and testable. Varaha's app is
   data-collection; credit computation is opaque/backend and not surfaced.
5. **Verifier portal for auditors.** A dedicated review/issue/export surface for
   verifiers — issue-credit is admin-gated, double-issue-safe, re-checks
   eligibility server-side, append-only audit trail. Varaha has **no
   auditor-facing product** (it's purely an ops app).
6. **GPS anti-fraud** (hardened this session): EXIF-GPS corroboration,
   mock-location detection, no-EXIF quarantine. Varaha GPS-tags media and checks
   boundary overlap, but no equivalent EXIF-mismatch quarantine surfaced.
7. **Security hygiene.** Varaha's *shipped* build has real holes our build does
   not: **secrets embedded in the bundle** (Maps/Firebase/Measure.sh keys), a
   **network traffic inspector (Inspektify) shipped in production** (anyone with
   the device can read all API traffic + tokens), APM pointed at a **test
   endpoint in production**, and **cleartext traffic enabled with no cert
   pinning**. Ours are fail-loud/gitignored secrets, no shipped inspector.
8. **RASP runtime defense (freerasp):** root/hook/debugger/emulator/repackaging
   callbacks, fail-closed. Varaha has PairIP (anti-repackaging wrapper) — roughly
   par on tamper-resistance, but no runtime threat callbacks.

---

## Head-to-head: security & data integrity (the video-worthy table)

| Dimension | Varaha (shipped) | TerraCipher |
|---|---|---|
| Local DB encryption | ❌ plaintext SQLite (PII, bank, signatures) | ✅ SQLCipher |
| Per-submission crypto signing | ❌ JWT bearer only | ✅ Ed25519 + replay window |
| Sensor-grounded burn data | ❌ photo/video stages | ✅ ESP32 BLE thermocouple + telemetry |
| Hardware attestation | ❌ none surfaced | ✅ ESP32 secure element (+ Play Integrity scaffold) |
| Transparent credit engine | ❌ opaque/backend | ✅ CSI 8-step + C0–C10 gates, signed audit |
| Auditor/verifier product | ❌ none | ✅ verifier portal (issue/export/audit) |
| Secrets in app bundle | ❌ multiple keys embedded | ✅ fail-loud, gitignored |
| Debug tooling in prod | ❌ Inspektify inspector shipped | ✅ none |
| Cleartext traffic | ❌ enabled, no pinning | ~ verify (portal is HTTPS) |

## Head-to-head: product breadth (where they win)

| Dimension | Varaha | TerraCipher |
|---|---|---|
| Farmer KYC + payments + FPIC consent | ✅ full module | ⚠️ text stub |
| Logistics / dispatch / receiving | ✅ end-to-end | ⚠️ end-use only |
| Map boundary capture + overlap checks | ✅ | ❌ |
| ML Kit doc scanner / barcode / OCR path | ✅ | ❌ (planned) |
| Multi-role / facility / country / program | ✅ | ⚠️ single-flow |
| In-app updates / feature flags / What's New | ✅ Firebase | ❌ |
| iOS | ✅ (KMP) | ⚠️ Flutter, Android-focused |
| Shipping in production at scale | ✅ v1.6.2, 3 countries | ❌ pre-production |

---

## Strategic read (the "so what")

- **Our differentiator = trust.** If a buyer or auditor asks *"prove this credit
  is real and this data wasn't faked,"* our architecture (signed evidence +
  hardware temperature attestation + encrypted-at-rest + transparent engine +
  verifier portal) answers materially better than a photo-and-JWT ops app. Lead
  the pitch with defensibility.
- **Their differentiator = they can run the business today.** We must not pretend
  otherwise. To compete on the actual job-to-be-done ("run a biochar supply
  chain"), we need the breadth items below.
- **What to borrow from them (fast wins):** the farmer KYC/payments/FPIC module,
  map boundary capture, the ML Kit document-scanner pipeline (also unblocks the
  moisture-meter OCR idea), the media preprocess + upload-progress pipeline, in-app
  updates + Remote Config feature flags, and iOS.
- **What they should borrow from us (and can't easily):** SQLCipher encryption,
  per-submission signing, sensor-grounded burn evidence, and a verifier portal —
  these are architectural, not features they can bolt on in a sprint.

## Fair-fight caveats (say these in the video to stay credible)

- Varaha is a **shipped v1.6.2**; we are **pre-production**. Some of our "wins"
  are architectural intent that still needs the last-mile (CI, attestation-on,
  cert pinning verification).
- Their security findings are from *their shipped binary* — real, but a company
  at their scale can fix them fast; don't overclaim permanence.
- This compares ONE Varaha app (field ops). Their credit computation, registry
  integration, and back-office are not in this binary and may be strong.
