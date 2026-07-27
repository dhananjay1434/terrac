# TerraCipher — Master Story & Narrative Playbook

**Purpose:** one source of truth for the company story. Every pitch, deck, website section, and sales call draws from here — same facts, same arc, tuned per audience.
**Rule:** nothing in the DECK layer may exceed what the PROOF layer supports. When in doubt, understate the claim and overstate the evidence.

---

## 1 · The core narrative (the arc every version follows)

**The carbon market has a trust problem, not a supply problem.**

Buyers have been burned. Registries are tightening. The market is repricing from "cheap credits" to "credits that survive scrutiny." In that market, the winner is not whoever removes the most carbon — it's whoever can **prove** removal in a way no auditor, buyer, or journalist can break.

**We built the proof machine first — then ran real carbon through it.**

- Two enhanced rock weathering (ERW) pilots across two Indian states — different geologies, different agronomic contexts — with mine contracts securing feedstock at the source.
- 4,000+ tonnes of biochar produced and applied, supplied into Varaha — one of the largest biochar programs in the world, backed by WestBridge Capital.
- And underneath all of it: our own dMRV — mobile capture (Android + iOS) to web verification dashboard — where every piece of field evidence is cryptographically signed on the device that captured it, hash-chained, and walked through the full Rainbow/CSI compliance gate set (C0–C10) before a single credit can be issued. Compatible with Rainbow, CSI, and Isometric requirements.

**The punchline:** most MRV software tracks what people *type in*. Ours proves what actually *happened* — device-held keys, signed evidence, tamper-evident hashes, and an issuance flow that is physically incapable of issuing a credit past a failed compliance gate. We didn't add security to an MRV tool; we built an evidence system that happens to do MRV.

**Where this goes:** every ton we sequester makes the proof machine more credible; every buyer who audits us makes the next sale shorter. The pilots are the demonstration. The dMRV is the moat. The market is everyone who needs carbon they can defend.

---

## 2 · Proof-point inventory (the PROOF layer)

Map every claim to its evidence *before* it goes in any deck. Fill the right column with actual document names/links.

| # | Claim (deck-safe phrasing) | Evidence to attach | Status |
|---|---|---|---|
| P1 | Two ERW pilots executed, in two different states | Pilot reports, application records, geotagged field photos, lab soil/rock analyses | have — attach |
| P2 | Mine partnerships securing basalt/feedstock supply (3–4 contracts) | Signed contracts / MoUs (redact commercials) | have — attach |
| P3 | 4,000+ tonnes of biochar produced & applied | Production logs, dispatch records, application evidence — *ideally exported straight from our own dMRV* | have — attach |
| P4 | Supplier to Varaha (WestBridge-backed, ~₹1,000 cr reported valuation) | Supply agreements / POs / delivery acknowledgments | have — attach |
| P5 | In-house dMRV aligned with Rainbow, CSI & Isometric requirements | Compliance-gate mapping doc (C0–C10 ↔ methodology clauses), sample evidence pack PDF, registry export files (CSI + Rainbow formats) | have — package it |
| P6 | Device-level cryptographic evidence integrity | Security architecture one-pager: device signatures, HMAC auth, SHA-256 evidence hashes, sealed issuance flow | write from existing backend docs |
| P7 | Full-stack: Android + iOS field apps + web verifier dashboard | Live demo + screenshots (use the portal's evidence pack print for the "wow" artifact) | ready after portal polish |
| P8 | Coverage across industrial, distributed, and artisanal biochar | Kiln registry + telemetry records showing both open/artisanal and industrial flows | have — attach |
| P9 | Lab-verified quality (H:Corg, organic carbon, permanence tiers) | Lab certificates + the dashboard's permanence-tier analytics | have — attach |

---

## 3 · Claim hygiene (what we say vs. what we never say)

These phrasings survive due diligence. The banned versions invite one fatal question.

| ✅ Say | ❌ Don't say | Why |
|---|---|---|
| "4,000+ tonnes of **biochar** produced and applied" | "4,000 tonnes of carbon removed" | Biochar tonnes ≠ CO₂e tonnes. When you have the CO₂e figure from the LCA engine, state both: "4,000+ t biochar → X t CO₂e sequestered (LCA-net, lab-verified)." The precision *is* the pitch. |
| "Evidence signed **on-device** at capture — a level of evidence integrity we have not seen in any commercial MRV" | "Cryptography that no company in the world is doing" | The absolute claim is unverifiable and invites a counterexample. The comparative-with-hedge version says the same thing and is undefeatable. |
| "Supplier to Varaha (backed by WestBridge Capital; reported valuation ~₹1,000 cr)" | "Our client is worth ₹1,000 crores" | Their valuation is *their* press claim — cite it as reported. Our verifiable fact is the supply relationship. |
| "Aligned with Rainbow and CSI methodologies; export formats for both; Isometric-compatible data model" | "Certified by Rainbow/CSI/Isometric" | Alignment/compatibility is provable today; "certified" is a specific status — only claim it when the certificate exists. |
| "Compliance gates C0–C10 enforced in software — a credit **cannot** be issued past a failed gate" | "Fraud-proof" | The first is an architecture fact we can demo live. Nothing is "fraud-proof" and claiming it paints a target. |

---

## 4 · The story, cut per audience

### 4.1 Investor (90 seconds)

> Carbon markets are repricing around one question: *can you prove it?* Buyers who paid for junk credits now pay premiums for auditable ones. We're an ERW + biochar company that answered the proof question with infrastructure, not paperwork.
>
> In the last cycle we ran ERW pilots in two states, locked mine contracts for feedstock, and produced 4,000+ tonnes of biochar — supplied into Varaha, the WestBridge-backed carbon project developer. So the operations are real and revenue-validated.
>
> The asset under it is our dMRV. Field evidence is cryptographically signed on the capturing device, hash-chained, and pushed through every Rainbow/CSI compliance gate in software — the system is architecturally incapable of issuing a credit that fails a gate. Android, iOS, web verifier portal, registry-ready exports. MRV is where every carbon deal now lives or dies, and we own ours end to end — it works for industrial plants and for ten thousand distributed artisanal kilns, which is where India's supply actually is.
>
> Pilots prove the science. Varaha proves the demand. The dMRV is the moat. We're raising to scale from pilots to programs.

### 4.2 Buyer / offtaker (credits or biochar)

Lead with *their* risk, not our tech:

> Every credit you buy is a claim someone might one day challenge. Ours ship with the evidence attached: geotagged, timestamped, device-signed photos of every batch; lab-verified permanence (H:Corg tiers); full LCA deductions shown line by line — safety margin, transport, methane — before the net figure. You can open any batch in our verifier portal and walk the same checklist our verifiers walk, gate by gate. 4,000+ tonnes already delivered this way, including into Varaha's program. You're not buying our word; you're buying the audit trail.

### 4.3 Registry / methodology partner (Rainbow, CSI, Isometric)

> We built our dMRV *from* your methodology, not toward it: the C0–C10 gate set is encoded as enforcement logic, not guidance. Provisional batches stay provisional until every hard gate clears — moisture corroboration ratios, telemetry thresholds, kiln registration, annual methane verification. Evidence is device-signed at capture and hash-verified at rest; the issuance action is irreversible, logged, and gated behind typed confirmation. We'd like to be the reference implementation for artisanal-scale digital MRV in India.

### 4.4 Mine / industrial partner

> Your overburden and waste rock streams have a second life as climate infrastructure. We've done this with [3–4] mines already: we handle characterization, application, monitoring, and the full evidence chain — you get a new revenue line and an ESG story backed by data, not adjectives.

---

## 5 · One-liners & taglines (pick per surface)

- **"Carbon you can defend."** (buyer-facing, lead candidate)
- "The proof machine for carbon removal."
- "We don't ask you to trust us. We hand you the evidence."
- "Removal is chemistry. Credits are proof. We do both."
- "MRV where the M actually happened." (edgy — social/blog only)

---

## 6 · The demo moment (the story's climax — script it, never wing it)

The portal we've built (and are polishing) is the *show-don't-tell* asset. The 3-minute walkthrough:

1. **Open the Batches list** — point at the status column: "every batch is provisional until proven."
2. **Open a provisional batch** — show the failed gate ("this one is missing lab H:Corg — the system will not let anyone issue it. Not won't: *can't*.")
3. **Open the hero batch** — walk the checklist: 10/10 gates, evidence gallery with SHA-256 fingerprints and GPS, lab-verified permanence tier, the LCA formula with deductions *subtracted in front of you*.
4. **Show the issuance flow** — the typed-confirmation modal: "irreversible actions look irreversible here."
5. **Print the evidence pack** — hand them the PDF. "This is what ships with every credit."

The demo's emotional beat: *most MRV demos show dashboards; ours shows a system refusing to lie.*

---

## 7 · Numbers block (keep current; single source for all decks)

| Metric | Value | Source |
|---|---|---|
| ERW pilots | 2 (two states) | pilot reports |
| Mine contracts | 3–4 | contracts |
| Biochar produced & applied | 4,000+ t | production/dispatch logs |
| CO₂e sequestered (LCA-net) | **fill from credit engine** | dMRV export |
| Marquee customer | Varaha (WestBridge-backed) | supply agreement |
| Methodology coverage | Rainbow, CSI (exports live); Isometric-compatible | gate-mapping doc |
| Field app platforms | Android + iOS | app builds |
| Compliance gates enforced | C0–C10, hard-gated issuance | codebase / demo |

---

## 8 · Gaps to close before the story goes public

1. **Compute and publish the CO₂e-net figure** for the 4,000 t — the LCA-net number is more powerful than the biochar tonnage and only we can produce it credibly.
2. **Package the security one-pager** (P6) — the crypto story is the differentiator and currently lives only in code.
3. **Finish the portal polish** (`portal/audit/REMEDIATION_BLUEPRINT.md`) — the demo is the climax; the dark-theme verdict bug and print evidence pack must be fixed before any live walkthrough.
4. **Get one quotable line from Varaha** — a single sentence from the buyer converts P4 from a contract into a story.
5. **Confirm the "two states" / "3–4 mines" specifics** — decks need the actual state names and mine count pinned.
