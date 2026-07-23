# Path to Real Credit Issuance — Readiness Spec

**The question this answers:** what must be true before this system can mint *real* biochar
carbon credits that an independent verifier (VVB) and a registry will actually accept and
issue as serialized units.

**Target methodology (already the code's target):** **CSI Artisan C-Sink** (Carbon
Standards International) — the code computes against `CSI-3.2` constants and ships a
`CSIExportService`. This is the correct registry for artisanal / Kon-Tiki flame-curtain
biochar in developing economies. Everything below is measured against *that* bar, not
against feature-parity with a competitor.

**The honest headline:** the remaining blockers are **mostly process and one architecture
piece — not features.** A prettier app does not get you issuance. What gets you issuance is
(1) proof the credit math conforms to the methodology, (2) a credit that exists as a
serialized, non-reissuable unit, (3) an enforced independent-verification step, and
(4) the data being trustworthy enough (sampling + calibration) that an auditor can't poke a
hole in it. In that order.

---

## What already clears the bar (do NOT rebuild these)

Grounded in the current code, these are real and issuance-relevant:

- **Tamper-evident evidence chain** — every artifact Ed25519-signed on-device, SHA-256
  hashed, and the hash **re-verified server-side** before storage (`media.py` recomputes and
  rejects on mismatch). PII encrypted at rest (SQLCipher).
- **Permanence gate** — lab H/Corg + Corg ingested through an authenticated lab channel,
  range-constrained at the DB layer, and it recomputes the credit. This is the single most
  important scientific input for biochar permanence, and it exists.
- **Server-side credit engine** — LCA computed server-side (no client-trusted inputs),
  emits a signed `lca_signature`, config-driven via `RegistryConfig`.
- **Compliance gates C0–C10** — default-ON, credit-blocking, render machine-readable reasons.
- **Registry export** — `GET /batches/{uuid}/export/csi` projects a schema-complete batch
  (inputs, lab, moisture/composite/transport, evidence media with hashes + verification
  status, credit + lca_signature) and **refuses provisional or unsigned batches**.
- **Verifier role + portal + per-media reviewer verdict** (approve/reject-with-reason),
  append-only audit trail, PII-access surface.
- **Anti-double-count at source** — unique batch UUID, parcel-overlap rejection across
  projects with an advisory lock.
- **Chain of custody** — composite-sample QR ties physical sample ↔ digital record ↔ lab.

That's a genuinely strong base. The gaps below are what stands between it and issuance.

---

## P0 — Blocks issuance entirely. Nothing mints without these.

### 1. Methodology-conformance validation + sign-off  ·  [PROCESS, not code]
**Gap.** The credit math uses `CSI-3.2` constants and is well-tested — but *tested code ≠
methodology-correct credit*. A VVB verifies the **formula against the CSI methodology**, not
our unit tests. There is no document mapping each CSI Artisan C-Sink equation → our code →
a validation that they match, and no qualified carbon-methodology reviewer has signed it.
**Why it blocks.** A registry will not issue against an unvalidated quantification. This is
the credibility gate, and it is the #1 blocker.
**Do.** (a) Write a conformance memo: every CSI-3.2 formula and constant, the exact code
path that implements it, and a worked example reproducing CSI's own reference calculation.
(b) Reconcile the "captured-but-not-wired" inputs — confirm whether CSI-3.2 *requires*
anything we capture but don't apply to the credit (e.g. methane rate, biomass→biochar
conversion factor), or applies a default where the methodology demands a measured value.
(c) Get it reviewed by a carbon-methodology expert or CSI directly, ideally a pre-validation
consultation.
**Unblocks.** The right to claim the number is real. External dependency — start now; it has
the longest lead time and no code can shortcut it.

### 2. Credit issuance ledger — serialized, non-reissuable units  ·  [ARCHITECTURE + FEATURE]
**Gap.** We compute `net_credit_t_co2e` per batch, but a "credit" today is just a *number on
a batch*. There is no issuance lifecycle: no serial number, no vintage, no status
(pending → verified → issued → retired/cancelled), no immutability once issued, no record of
what was submitted to the registry. `mint` in the codebase refers only to enrollment tokens.
**Why it blocks.** A registry credit is a *serialized unit* traceable to one physical
production event and issuable exactly once. Without a ledger you cannot prevent re-issuance,
cannot report vintages, and cannot answer "which physical batch produced serial X."
**Do.** New `CreditIssuance` model + lifecycle: (batch_uuid → serial, vintage, tCO2e frozen
at issuance, status enum, issued_at, verifier_id, registry_submission_ref, immutable after
issued). State machine (pending → independently-verified → issued → retired), append-only,
signed. Portal issuance workflow gated on P3 below.
**Unblocks.** Credits existing as real, auditable, non-double-issuable units. ~1–2 weeks.

### 3. Enforced independent verification (4-eyes) before issuance  ·  [FEATURE + gate]
**Gap.** Our entire evidence chain still has **one root of trust: the producing operator's
phone**. Signing proves "this device sent it untampered" — not "the burn really happened."
CSI Artisan C-Sink mitigates exactly this with mandatory independent audit + supervisor
oversight. We have `supervisor_visit` registry *data* but no *enforced* rule that a
non-producer must verify a batch before it can issue.
**Why it blocks.** This is the fraud-resistance the methodology assumes. Without it, a
colluding operator's staged batch passes every cryptographic check.
**Do.** Make independent verification a hard state on the issuance path: a batch cannot enter
`issued` until a distinct verifier/supervisor (not the producing device/operator) signs off,
recorded immutably. Reuse the existing `verifier` role and per-media verdict; add the
batch-level gate. Encode CSI's required verification frequency/coverage.
**Unblocks.** The credibility of every credit against the "how do you stop a fake burn?"
question. ~days–1 week.

---

## P1 — Data won't survive audit scrutiny without these.

### 4. Sampling-plan enforcement  ·  [FEATURE + gate]
**Gap.** We capture composite samples + per-batch lab results, but we do not *enforce* CSI's
representative-sampling rule (e.g. minimum sample frequency per tonne / per period per
facility, and the compositing rule). A facility could run 50 batches against one lab result
and the system would still export them.
**Why it blocks.** An auditor checks that lab coverage is representative per the methodology;
under-sampled batches are not issuable.
**Do.** Encode the CSI sampling frequency as a gate: a batch is issuable only if it's covered
by an in-scope lab result within the methodology's sampling window/compositing rule. Link
each lab result to the exact set of batches it represents.
**Unblocks.** Lab-coverage defensibility. ~days–1 week.

### 5. Instrument-calibration enforcement (all instruments)  ·  [FEATURE + gate]
**Gap.** We have scale + bulk-density calibration and a `production_requires_valid_density`
gate. But calibration validity should gate issuance for **every** credit-affecting instrument
— crane/weigh scale, BLE thermocouple, moisture meter — with an in-date certificate required.
**Why it blocks.** Uncalibrated measurement = untrustworthy mass/moisture/temperature =
rejectable credit.
**Do.** Extend the existing calibration-gate pattern to thermocouple + moisture meter;
require an in-date calibration record per instrument or block the batch. Surface expiry.
**Unblocks.** Measurement trust. ~days.

### 6. Reproducible verification package (project/period level)  ·  [FEATURE]
**Gap.** We export per-batch. A VVB verifies at *project/period* level and wants to
**independently re-derive** the credit from the exported inputs and get the same number.
`lca_signature` proves the number wasn't altered post-hoc; it doesn't let the auditor
reproduce it.
**Why it blocks.** "Trust our number" fails audit; "here are the inputs, re-run the published
formula, get the same tCO2e" passes.
**Do.** (a) Project/period verification bundle aggregating batches + evidence + lab + credit.
(b) A published, versioned calculation spec (falls out of P0.1) the auditor can reproduce
against the export. (c) Sample-retention linkage (physical biochar sample ID ↔ lab ID ↔
batch) — the composite-sample QR already gives the backbone.
**Unblocks.** The literal "registry can verify it" ask. ~1–2 weeks (partly P0.1's output).

---

## P2 — Required to be in production at all (not methodology, but hard prerequisites).

### 7. Deployment hardening  ·  [TECH / OPS]
- **Scrub + rotate the committed `demo_secrets.bat`** (`DMRV_HMAC_SECRET`/`DMRV_ADMIN_SECRET`
  are in git history) — and purge from history. Blocks any credible security review.
- **Live hosted Postgres backend** (the backend already refuses to boot without
  `DATABASE_URL`; stand up the real one).
- **Signed release builds** (Android now; iOS per `IOS_BUILD_RUNBOOK.md` — still
  macOS-unverified).
- **Turn on / calibrate the dormant capture gates** (`DMRV_BLUR_GATE_ENFORCED`,
  `DMRV_GEOFENCE_CAPTURE` currently default-off) *after* field calibration, or stop counting
  them as controls.
**Unblocks.** Being deployable and passing a basic security posture check.

---

## Verdict — is it feature, tech, or architecture?

- **Feature:** the smallest part. Items 3, 4, 5 are gates on top of things we already capture.
- **Architecture:** one real piece — the **issuance ledger (P0.2)**. Everything else reuses
  existing rails.
- **Tech/ops:** deployment hardening (P2) — necessary, straightforward.
- **Process:** the **biggest and longest-lead blocker — methodology conformance sign-off
  (P0.1)** — and it cannot be coded around. Start it first and in parallel with everything.

**Sequenced path to first real issuance:**
1. Kick off **P0.1 (methodology sign-off)** immediately — external, longest lead.
2. Build **P0.2 (issuance ledger)** + **P0.3 (independent-verification gate)** in parallel.
3. Add **P1.4/5 (sampling + calibration gates)** and **P1.6 (verification package)**.
4. **P2.7 (deployment hardening)** before any live pilot.

Only after P0.1 returns a clean conformance sign-off, a batch has passed independent
verification, and it flows through the issuance ledger into a serialized unit — is a credit
"real." The code is ~70% of the way there; the missing 30% is disproportionately the
process/validation and the ledger, not screens.
