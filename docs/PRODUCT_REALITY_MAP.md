# Product Reality Map — TerraCipher vs Varaha (peer, brutal)

**Ground rule:** both are small companies shipping a biochar field-MRV product. Funding,
deals, headcount removed. Only question: **which product better does the job — mint credits
a registry issues and a buyer trusts.** All claims below are checked against our source and
their reverse-engineered shipped binary.

---

## The bar: what makes a biochar dMRV product production-ready

1. **Capture** a full production cycle offline, reliably.
2. **Trust** — evidence an auditor accepts as un-fakeable.
3. **Conformance** — credit math validated against a real methodology.
4. **Issuance** — credits as serialized, issue-once units traceable to physical events.
5. **Deploy** — secure, multi-operator, actually running.

## Scorecard against the bar

| Bar | Us | Them | Who's ahead |
|---|---|---|---|
| 1. Capture completeness | Full cycle, but thinner evidence per step | Full cycle + richer evidence (video/PDF/scanner) | **Them** |
| 2. Evidence trust | Signed + hash-verified + encrypted | Unsigned metadata + plaintext + shipped holes | **Us, clearly** |
| 3. Conformance | Math built, unvalidated; Rainbow annexes stubbed | Math server-side (unseen); unvalidated to us | Even / unprovable |
| 4. Issuance | **None** (credit = a number on a batch) | Presumed server-side (not in app) | **Them (by default)** |
| 5. Deploy | Cleaner security, sloppy secrets, iOS unverified, not live | Live 3 countries, iOS shipping, security holes | **Them on reach, us on posture** |

**One line: they have the more complete product; we have the more trustworthy one.**

---

## WHERE WE LOSE — the fix-list (categorized, each with why it matters)

### Features (they ship these; we don't)
- **F1. Day-start audit is checkbox-only.** Theirs = facility photo + walkthrough video that
  locks the audit. Ours (just built) has no camera. *Auditor asks "prove the operator
  actually checked, not just tapped."* — hygiene, cheap, embarrassing to lack.
- **F2. Quench is photo-only.** Theirs requires a **quenching video** at that stage. Quench
  is the permanence-critical moment; video is stronger evidence. We already have video
  capture — it's just not required here.
- **F3. Bulk-density test has no video.** Theirs records a video of the weighing. Numbers
  alone are more spoofable than a video of the act.
- **F4. No document scanner.** Theirs uses ML-Kit doc scanning (edge detect, perspective) for
  IDs/land docs/invoices. Ours = plain photo. Quality-of-capture for KYC/disputes.
- **F5. No on-device PDF generation.** Theirs builds weight-slip/consent PDFs on device.
  Ours references a PDF but generates none. Auditor presentation polish.
- **F6. No task/work-assignment system.** Theirs assigns and tracks field-staff work. Ours
  has none. Fleet-ops management, not credit integrity.
- **F7. Single country / single payment rail.** Theirs: India/Bangladesh/Kenya field configs
  + UPI/bKash/M-Pesa. Ours: India + bank only. Only matters if you expand.

### Tech
- **T1. Media routes through our backend, not presigned-S3.** Theirs PUTs direct to S3;
  their API just issues credentials. Ours streams every file through FastAPI. Bites at
  scale (bandwidth/cost).
- **T2. Our capture-integrity gates ship OFF.** Blur rejection + geofence-at-capture exist
  but `defaultValue: false`. So a blurry/off-parcel photo passes at capture; only *maybe*
  caught later by review. Either calibrate + enable, or stop counting them as controls.
- **T3. Not actually deployed.** No confirmed live hosted Postgres, Android release signing
  pipeline, or iOS build (runbook only). Theirs is live on both stores.
- **T4. Committed secrets.** `demo_secrets.bat` (HMAC + admin secrets) is in git history.
  Scrub + rotate + purge — this fails a basic security review on sight.

### Architecture
- **A1. No credit issuance ledger.** A "credit" is a number on a batch — no serial, vintage,
  status (pending→issued→retired), immutability, or registry-submission record. Registry
  credits are serialized, issue-exactly-once units. **This is the biggest architecture gap.**
- **A2. No sync-conflict state.** Theirs has explicit `CONFLICT`; ours has pending/failed but
  no server/client-divergence resolution path.
- **A3. Methodology is not a first-class switch.** Today, *every* batch: gated by **Rainbow's**
  C0–C10 rules, computed with **CSI-3.2** math, exported as a generic JSON + a label. That's
  one path wearing two labels — not two methodologies. To do CSI *and* Rainbow for real, the
  project's methodology must select the gate-set, the LCA params/formula, and the report.

### Process (not code — but these gate issuance harder than any feature)
- **P1. No methodology-conformance sign-off** (CSI *and* Rainbow). Tested code ≠ correct
  credit; a VVB checks the formula against the methodology. Longest lead, external, start now.
- **P2. Rainbow's numeric annexes are stubbed** (`emission_factors.py`: transport factors are
  placeholders, `TRANSPORT_EVENTS_ENFORCED=False`, "do not invent factors"). Rainbow batches
  currently compute with CSI-3.2 numbers by default. Fill + cite the real Rainbow constants.
- **P3. No enforced independent (4-eyes) verification** before issuance. We have supervisor
  *data*, not an enforced "a non-producer must sign off" gate. This is the methodology's
  fraud mitigation.
- **P4. Sampling-plan + all-instrument calibration not enforced as issuance gates.** We gate
  on density; extend to the methodology's lab-sampling cadence + scale/thermocouple/moisture
  calibration validity.

---

## WHERE WE WIN — and the honest mechanism for each

- **W1. Signed evidence (Ed25519 device signature + server-side SHA-256 re-verification) vs
  their unsigned metadata.** *Why it's real:* their GPS/FOV/tilt/blur is annotation anyone
  controlling the client can edit; ours is a cryptographic proof that *this device produced
  these exact bytes, unaltered*, re-checked server-side before storage. For a product whose
  entire value is trust, this is the axis that matters most, and it's not close.
- **W2. Encrypted PII at rest (SQLCipher) vs their plaintext SQLite.** *Why it's real:* their
  own teardown flags farmer signatures, Aadhaar refs, bank/IFSC/UPI sitting in plaintext as a
  finding. In a DPDP/data-protection review, that's a fail for them, a pass for us.
- **W3. Cleaner shipped security.** *Why it's real:* their production build ships a
  shake-to-open network traffic inspector (leaks tokens), an APM key pointed at a test host in
  cleartext, and `usesCleartextTraffic=true` with no cert pinning — all concrete, all in the
  binary. Ours has TLS-pinning options, RASP, a remote kill-switch, and no shipped debug tooling.
- **W4. Credit-blocking compliance gates default-ON with machine-readable reasons.** A deeper
  *enforced* protocol layer than their visible CRUD + per-media verification-status model.
  *Caveat:* their real gating may live server-side where we can't see it — so call this
  "ahead on what's visible," not proven.

**Where "better" is actually just "unproven" (don't oversell):** credit-math depth (theirs
is server-side, invisible), test rigor (theirs invisible), offline sync (both mature — they
have conflict state, we have signing). These are even or unscoreable, not wins.

---

## The ceiling neither product breaks

Both root **all** evidence in one operator's phone. Signing makes ours tamper-evident in
transit; it does nothing against a *staged* burn at capture. Neither field app corroborates
independently. Their *platform* does (remote sensing / land-use cross-check); **ours does
nowhere.** For biochar, satellite matters less — but a cheap independent signal (declared
feedstock mass vs the parcel's plausible residue yield; anomaly-flagging operators;
mandatory supervisor re-verification) is the real long-term differentiator, and it's open
for us.

---

## Brutal verdict + fix priority

**Product-to-product, peer-to-peer: they win completeness, we win trust.** Completeness is
catch-up work (bounded, known). Trust is the hard thing to build and the thing that actually
mints credits — and we're ahead on it. So the strategy writes itself:

**Tier 0 — makes credits real (do first; mostly process + one architecture piece):**
P1 conformance sign-off · A1 issuance ledger · P3 independent-verification gate · P4
sampling/calibration gates · P2 fill Rainbow annexes.

**Tier 1 — makes the evidence audit-proof (cheap, high-trust-yield):**
F1 day-start photo/video · F2 quench video · F3 density video · T2 turn on the capture gates.

**Tier 2 — makes it deployable:**
T4 secret scrub · T3 hosted backend + signed builds + iOS · A3 methodology-as-switch (needed
before you truly run both CSI and Rainbow).

**Tier 3 — breadth, only when you need it:**
F4 doc scanner · F5 on-device PDF · F6 tasks · F7 multi-country · T1 presigned-S3 · A2 conflict state.

**The sentence to remember:** *don't chase their feature breadth to feel competitive — it
loses to the thing you already do better. Double down on trust (issuance + conformance +
independent verification), cherry-pick only the capture gaps an auditor actually checks
(day-start/quench/density evidence, sampling, calibration), and skip the ops-breadth until
scale forces it.* That path makes it production-ready AND keeps you genuinely better on the
one axis that decides whether a credit survives.
