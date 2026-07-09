# CBAM dMRV — Deep-Research Prompt (paste-ready)

*Purpose: a single, self-contained brief to hand a deep-research AI (or a research
analyst). It produces the regulatory + industry + technical foundation needed to decide
whether — and how — to extend our existing biochar dMRV platform into a CBAM compliance
product. Everything below the line is the prompt. Fill the two `<<...>>` blanks first.*

---

## HOW TO USE
1. Replace `<<TARGET_MARKET>>` (e.g. "mid-size Indian chemical/textile/metal exporters to the EU")
   and `<<TODAY>>` (today's date) below.
2. Paste the whole "PROMPT BEGINS" block into a deep-research tool with web access.
3. Non-negotiable rule to enforce: **every regulatory number, deadline, threshold, or
   certificate-field claim must carry a primary-source citation** (the EU regulation, an EU
   Commission page, or an official guidance PDF) with a retrieval date. Secondary blogs are
   allowed only for industry-practice color, never for a compliance requirement. If a fact
   cannot be primary-sourced, it must be labelled `UNVERIFIED` — not stated as fact.

---

## ===== PROMPT BEGINS =====

**Role.** You are a senior regulatory + carbon-accounting analyst with a software-architecture
background. You are advising a technical founder who already operates a working, offline-first,
cryptographically-signed **dMRV (digital Measurement, Reporting & Verification) platform**
built for distributed biochar carbon-credit capture (Ed25519 device signing, hashed
GPS/EXIF-stamped photo evidence, transactional offline outbox, an evidence-grading engine that
marks records "provisional" until every required check passes, transport-leg telemetry, and a
stepwise signed emissions calculation). The founder is evaluating building a **second product:
a CBAM compliance / provenance dMRV** for `<<TARGET_MARKET>>`. Today is `<<TODAY>>`.

Do exhaustive, primary-source-grounded research and produce the structured report specified in
"OUTPUT" below. Be brutally honest about uncertainty, regulatory flux, and where the founder's
existing assets do **not** transfer. Do not pad. Do not invent numbers.

### PART A — CBAM regulatory mechanics (the hard requirements)
Establish, with primary EU sources and retrieval dates, the current state as of `<<TODAY>>`:

1. **Scope & timeline.** Which goods/CN codes are in scope now (iron & steel, aluminium,
   cement, fertilisers, hydrogen, electricity — confirm the current list and any additions).
   The exact status and dates of the **transitional period vs the definitive period**, and
   what changed at the definitive start (financial liability, CBAM certificate purchase,
   mandatory verification). Note the **2025 simplification/"Omnibus" changes** and the
   de-minimis mass threshold — confirm the current figure and what it exempts.
2. **Who is the obligated party** (EU importer / indirect customs representative / "authorised
   CBAM declarant") and what a **non-EU installation operator** (our customer, or our
   customer's customer) must supply to them. Clarify: our target is likely a *supplier* into
   the EU value chain, not the declarant — pin down exactly what data burden lands on the
   non-EU manufacturer.
3. **Embedded-emissions methodology.** How embedded emissions are calculated for in-scope
   goods: direct vs indirect emissions, **default values vs actual values**, the rules for
   using actual data, mass-balance / attribution to specific goods, and the treatment of
   **biomass** (when biomass combustion counts as zero-rated, and the *sustainability /
   provenance conditions* attached — this is the crux for our product). Cite the specific
   methodology annexes.
4. **Reporting artefact & data schema.** What the actual **CBAM report / declaration**
   requires field-by-field (installation data, production routes, emission factors, embedded
   emissions per tonne per good, carbon price paid in origin country). Identify the official
   **XML/schema or template** (the CBAM registry / communication template) and where its spec
   lives. This defines what any software must output.
5. **Verification & data integrity.** What third-party **verification** the definitive period
   requires (accredited verifiers, what they check, what evidence is acceptable). Crucially:
   **what makes emissions data auditable/acceptable vs rejected** — this is where our
   cryptographic-provenance angle either matters or doesn't. Be specific about whether tamper-
   evidence, source-signing, or continuous telemetry is *required*, *rewarded*, or *irrelevant*
   under the actual rules.
6. **Interaction with EUDR and CSRD.** Where the EU Deforestation Regulation (geolocation of
   land parcels, no-deforestation proof) and CSRD Scope-3 obligations overlap with CBAM for a
   biomass-fuel supply chain, and whether one provenance dataset can serve all three.

### PART B — Industry reality (what the target companies actually do today)
For `<<TARGET_MARKET>>` — and specifically test these named, publicly-documented biomass-
transitioning exporters where evidence exists: **Apcotex, Tatva Chintan, Jayant Agro-Organics,
Bodal Chemicals, Balaji Amines, Neogen, Jubilant Ingrevia, Rossari (chemicals); Pratibha
Syntex, RSWM, Banswara Syntex, Sangam, Nitin Spinners, Indo Count (textiles); Nelcast,
Steelcast, Alicon Castalloy, Rolex Rings, Talbros, Sandhar (metals)** — research:

1. **Current CBAM-compliance behaviour.** How are these firms actually handling CBAM reporting
   *right now*? Spreadsheets? Consultancies (Big-4, boutique)? An existing software vendor? In-
   house? Nothing yet? Find evidence, don't assume.
2. **Biomass provenance today.** For those burning biomass (briquettes, husk, bagasse,
   deoiled cake, wood waste), how — if at all — do they currently document fuel origin,
   sustainability, and transport emissions? Manual vendor declarations? Certificates? Nothing?
3. **The pain & the buyer.** Who inside these orgs owns CBAM (title), what does the failure
   mode cost them (lost EU market access, default high-carbon values, tariff exposure), and
   what are they willing to pay for. Identify the real buyer persona and budget reality.
4. **Incumbent competitors.** Who already sells CBAM/ESG/provenance software into this market
   (global and India-specific)? What do they do well and where's the gap — specifically, does
   anyone offer **source-level cryptographic provenance** vs. after-the-fact spreadsheet
   aggregation? Name them; assess their moats.
5. **The honest "do they even want dMRV" question.** Adversarially test the thesis: is
   cryptographic/field-level provenance something buyers actually demand, or is a good-enough
   consultancy + template sufficient for them to pass? Where is our differentiation real vs.
   over-engineered?

### PART C — Can AI agents / RAG genuinely solve parts of this? (be a skeptic)
For each area below, judge **where an LLM/agent/RAG adds real, defensible value vs. where it is
theatre or a compliance risk.** For each: what the AI approach is, why it helps, its failure
modes, and whether a regulator/verifier would accept AI-derived output.

1. **Regulatory-knowledge RAG.** A RAG over the CBAM regulation + annexes + guidance +
   CN-code tables answering "what applies to *my* product/route" and auto-mapping a factory's
   fuel/production data to the right methodology. Value? Hallucination/liability risk on a
   legal-compliance surface? How to constrain it (citations-required, retrieval-only,
   human-in-loop)?
2. **Document extraction agents.** LLM extraction of structured emissions/transport/provenance
   data from the messy real-world inputs these firms have — vendor invoices, weighbridge slips,
   boiler logs, transport bills, sustainability certs (multi-language, incl. Hindi/regional).
   This is likely the highest-value, lowest-risk AI use. Assess accuracy needs and
   verification.
3. **Emissions-calculation assistance vs. authority.** Can an agent *compute* embedded
   emissions, or only *assemble inputs* for a deterministic, auditable calculator? (Our
   existing engine is deterministic + signed — argue whether the calc must stay deterministic
   for audit defensibility and the LLM stays at the edges.)
4. **Certificate/report generation.** LLM-assisted drafting of the CBAM report/declaration
   from validated data — where it helps, and why the final artefact must be schema-validated
   and deterministic, not free-generated.
5. **Provenance anomaly detection.** ML/agent detection of fraud signals (impossible
   transport distances, mass-balance mismatches, duplicated evidence) layered on our signed
   evidence. Value vs. false-positive cost.
6. **Verdict.** Rank these by (value × feasibility × low-regulatory-risk). State plainly which
   are product features and which are traps.

### PART D — Reuse map against the existing platform
Given the founder's existing assets (identity/Ed25519 signing, offline outbox/sync, hashed
source-capture, transport-leg telemetry, a provisional-grading rule engine, a stepwise signed
emissions calc, FastAPI+async-SQLAlchemy+Alembic backend, Flutter+SQLCipher client):

1. Map each CBAM requirement from Part A to: **REUSE / ADAPT / BUILD-NEW / DROP**.
2. Identify the genuinely new capabilities (industrial boiler/meter data ingestion, ERP/MES
   shipment data, per-shipment carbon-intensity allocation, CBAM certificate/schema output,
   multi-tenant + RBAC enterprise surface, land-parcel/EUDR provenance) and rank by build
   difficulty + external dependency.
3. Flag the two known capability gaps (industrial-OT/meter integration; EU-regulatory
   implementation) and how much of the MVP can *defer* them (e.g. CSV/manual ingestion first).

### PART E — MVP definition & phased plan
1. Define the **smallest MVP that delivers real value** (one design-partner factory: validated
   provenance + transport + combustion data → one schema-valid, cryptographically-sealed
   carbon-intensity artefact). State explicitly what is **cut** from MVP (live SCADA, satellite
   EUDR, deep ERP, multi-party mass balance).
2. Give a **phased build plan** with rough engineer-week estimates per workstream, a critical
   path, and per-phase acceptance/test gates.
3. State the **non-engineering dependencies** that gate the timeline (a committed design-partner
   factory with real data; locking the exact regulatory schema in scope) and the risks.
4. Distinguish **"MVP that produces a certificate"** from **"certificate an accredited verifier
   accepts"** — quantify the gap.

### OUTPUT — format
- Lead with a **1-page executive verdict**: is this worth building, the single biggest risk,
  the single biggest reusable asset, and a go/no-go recommendation with reasoning.
- Then Parts A–E as structured sections with tables where useful.
- A **source table**: every regulatory claim → primary source URL + retrieval date + a
  confidence flag (`PRIMARY-CONFIRMED` / `SECONDARY` / `UNVERIFIED`).
- A **"what I could not verify"** section listing every open question, stale-risk fact, or place
  the regulation is ambiguous or changing — do not paper over these.
- Explicit **assumptions** and **date-sensitivity warnings** (CBAM is mid-transition; flag
  anything likely to change and when).

### RULES
- Primary sources for every compliance requirement; date-stamp everything; label `UNVERIFIED`
  rather than guess.
- **Never invent a regulatory value, threshold, factor, or certificate field.** A missing fact
  stated as missing is correct; a plausible fabricated one is a failure.
- Separate *what the regulation requires* from *what the market currently does* from *what we
  could sell* — never blur them.
- Be adversarial about the founder's thesis: argue the strongest case that cryptographic dMRV is
  over-engineered for CBAM, then rebut or concede it.

## ===== PROMPT ENDS =====

---

## Notes for the founder (not part of the prompt)
- **Why the citation rule is strict:** the same discipline as the biochar side — a wrong CBAM
  factor or a mis-stated deadline propagates into a certificate an auditor rejects. Treat every
  regulatory number as load-bearing until primary-sourced.
- **The Part C answer will likely be:** RAG-for-navigation + LLM-for-extraction are the real
  wins; the *calculation and the certificate must stay deterministic and signed* for audit
  defensibility — which is exactly what your existing engine already is. That's the honest
  place AI helps without becoming a liability.
- **Run this before committing engineering.** Its Part A (schema + verification rules) and Part
  E (design-partner dependency) are the two things that will actually move your timeline.
