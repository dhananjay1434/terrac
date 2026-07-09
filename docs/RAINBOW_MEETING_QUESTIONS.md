# Rainbow Meeting — Questions to Ask

Goal of this meeting: get the **GHG quantification document** (the actual numbers) and
confirm which compliance gates are mandatory for issuance. Everything else is secondary.

Context you can state up front: "Our dMRV captures every data point in your
*Distributed Biochar* criteria and gates issuance on a compliance checklist. We're
blocked on the quantification factors — the criteria doc lists the data required but
no emission factors, and the Service Agreement is commercial-only. Where do the numbers live?"

---

## 1. THE BLOCKER — get the quantification doc  ★ most important

- **"Can you send the GHG Reduction Quantification document / Table 3 for the
  Distributed Biochar (open-kiln) pathway?"** (The Service Agreement references a
  "Project Design Document & Monitoring Plan" — we need that, as a file.)
- Specifically, we need, **with units and source table**:
  - Transport fuel **emission factors** (kg CO₂e per litre, or per tonne-km) — diesel/petrol/etc.
  - The **methane (CH₄) treatment** in the credit: is it a measured rate → penalty, or a
    fixed factor? What GWP for CH₄ (GWP100 = 28? 25? which AR version)?
  - The **Corg / H:Corg permanence** formula + the 0.4 H:Corg tier boundary — confirm the
    exact decay coefficients (we implemented CSI Global Artisan C-Sink 3.2 — is that the
    right basis, or does Rainbow have its own?).
  - The **Margin-of-Safety** deduction and any other mandatory deductions.
- **"Is the methodology versioned? Which version do we build to, and how are updates communicated?"**

## 2. CONFIRM THE PATHWAY (clear up the confusion)

- **"Confirm this project is solid biochar from pyrolysis, not biogas / anaerobic digestion."**
  (Some quantification examples floating around use biogas numbers — BMP, slurry storage
  loss. Those are a *different* methodology and must not be used here. We want written
  confirmation it's the biochar C-Sink pathway.)

## 3. WHICH GATES ARE MANDATORY FOR ISSUANCE (what blocks a credit)

Ask them to confirm, for each, "does a batch missing this block issuance, or is it advisory?":
- Scale calibration in-date
- Annual **methane measurement** (3 representative runs) — per project/period
- **PAH** test (closed-kiln) / heavy metals
- Kiln registered in the project registry
- Lab **Corg + H:Corg** (we currently require both before a final credit — confirm that's right)
- **"Is the 1000-year inertinite pathway required, or an optional election?"**
  (We treated it as optional — confirm.)

## 4. THE PROJECT/SITE LINKAGE (we need this to turn on 3 gates)

- **"How does a production batch map to a project and a specific weighing scale?"**
  (We have kilns/scales/annual-verifications keyed by project+year, but a *batch* has no
  project_id/scale_id yet. We need the identifier scheme to enforce calibration + annual
  methane/PAH per batch. 3 sites — how are sites/projects identified?)

## 5. DEVICE INTEGRITY / VERIFICATION EXPECTATIONS

- **"Does Rainbow require hardware attestation / anti-tamper on the field device, or is
  the auditor's on-site verification the control?"** (Today a rooted device's telemetry
  isn't cryptographically verified — we want to know if that's an issuance blocker.)
- **"What exactly does the annual 3rd-party verification audit inspect in the dMRV data?"**
  (So we expose the right compliance report / evidence to the auditor.)

## 6. LOGISTICS

- Sample/real **Project Design Document** from an existing biochar project, if shareable.
- Who is the **methodology point-of-contact** for follow-up number questions?
- Any **test/sandbox registry** we can validate against before real issuance?

---

## The one-liner if you only get 60 seconds
"Send us the biochar GHG quantification document with the emission factors, CH₄ treatment,
and CH₄ GWP — with units. That's the single thing blocking us from computing real credits.
Everything else we've built to your criteria doc."

---

## Why these (internal note)
- We read both repo docs: the criteria doc has **no** factors; the Service Agreement is
  commercial (€ fees) only. The real numbers are in a doc we don't have.
- Credit-math is deliberately OFF (`TRANSPORT_EVENTS_ENFORCED=False`, placeholder factors
  marked `TODO(cite)`) — we refuse to issue on guessed numbers.
- 3 gates (scale calibration, annual methane, PAH) are wired but dormant because a
  batch→project/scale linkage doesn't exist yet — Q4 unblocks them.
