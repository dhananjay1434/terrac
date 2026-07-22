# Varaha "Kalki" — Intelligence Dossier of Smart Things (primary-verified)

What Varaha does, how, and why it's clever — mined from the **shipped binary**
(decompiled `classes*.dex`, the base64 `strings.commonMain.cvr` catalog, DDL,
native libs), NOT the RE `.md` summaries. Every item marks **our status** (grep of
our `lib`/`backend`) and flags anything the RE docs claimed that could NOT be
confirmed in the binary. Point-out only — not a copy plan.

Note on provenance: veins A (methodology), B (field-UX), C (anti-fraud) are from
fresh primary-artifact mines this session. Vein D (sync) is drawn from the
earlier Platform deep-dive + the 06-SYNC RE map (the dedicated sync mine was
interrupted) — treated as slightly less independently re-verified.

---

## The one structural insight
Varaha's schema is a **physical mass-balance ledger with provenance at both
ends** (bounded source parcel → weighed in → produced → weighed out → applied),
plus a config-driven multi-program/multi-tenant platform. Ours is a
**single-batch, cryptographically-signed LCA calculator** with a verifier portal.
That difference explains every gap below — and every advantage.

---

## VEIN A — Methodology / data-model IQ (fresh primary)
1. **`site` = geo-fenced source parcel** (boundary + `boundary_method`/`status` + `crop_residue_history` + `farm_land_survey_number` + ownership) with **server-side overlap rejection** (`nearby-site-boundary`, `boundary_is_overlapping_with_existing_site`). Solves provenance + additionality + **double-counting** at write time. → **We model none of it.**
2. **`registry` + `registry_config_id` on facilities** (added by migration) → methodology + FPIC + rules are **config, not code**; one binary serves biochar/ARR/regen. → **We hardcode `CSI-3.2`.**
3. **`bulk_density` as an evidenced volume→mass activity** (`density_activity_video` + `mass_image`), **production hard-gated** on an in-date density (`production_data_can_not_be_added_without_bulk_density`); biochar mass = `batch_kiln.volume × density`. → **We capture density but never use it for mass** (direct crane weight only).
4. **Full mass-balance chain** with **dual weighing** (`empty_truck`/`loaded_truck` + `weight_at_facility` + weighbridge `weight_pdf`), per-source apportionment (`dispatch_sites`), and running `biomass_remaining`/`biochar_remaining` ledgers. → **We have one `wet_yield_kg` + a good plausibility ratio, no legs/ledger.**
5. **FPIC template by (projectType, state, district, language)** across 3 CDN program trees + an **exclusivity (no-double-sell) clause** stored as signed consent. → **We model no consent at all.**
6. **Two-level `tenant_id`→`organization_id` multi-tenancy** with org-approval lifecycle gates. → **We're single-tenant (role-only).** *Flag: the exact tenant HTTP header name is NOT in primary strings — only the scoping is proven.*
7. **Artisanal (kilns) vs industrial (gasifier) facility typing** with type-gated invariants. → **We have a kiln registry only, no facility typing.**
8. **`biochar_sample` → lab carbon link.** → **We're arguably AHEAD** (composite-sample + `corg_override` wired into the LCA).
9. **Moisture captured at every leg** (source/dispatch/input/kiln). → **We have single-node moisture (strong C2 rule).**
10. **Dung+biochar mixing video = soil end-use/permanence proof.** → **We prove permanence mathematically (H:Corg 100-yr decay) + delivery/buyer record.**
11. **Per-day `artisanal_summary` rollup + daily-media-before-cycle gate.** → **We have none.**

## VEIN B — Field UX ergonomics (fresh primary)
1. **Pincode → address auto-fill** (numeric entry replaces spelling place names) + review step. → **Absent.**
2. **IFSC → bank auto-lookup** + country-specific bank validators. → **Absent.**
3. **Truck-fill % "how full from previous farm"** — models shared-truck logistics with one tap. → **Absent.**
4. **Stage-labeled photo prompts** ("~90% of run, pre-quench, **kiln ID visible**"). → **Partial** (thinner copy).
5. **Fit-to-box / dashed-oval framing overlay.** → **Partial** (we have a moisture-meter crosshair overlay + front/back lens).
6. **Day-start audit that LOCKS** the day's logging until proof captured. → **Partial** (we lock on moisture instead).
7. **Save-to-Draft everywhere** + Drafts area. → **Absent.**
8. **Consequence-explicit confirm dialogs** ("…you cannot change weight details"). → **Weak.**
9. **"Reading X of N" / step counters.** → **Parity.**
10. **Role switch (Site↔Facility) + facility selector gating.** → **Absent.**
11. **Unsynced counts/badges + logout-loses-data guard + low-internet pause.** → **Parity / arguably stronger** (Sync Health screen).
12. **Actionable empty-state guidance** on every list. → **Partial.**
13. **Saved-number login + unsynced-media login nudge.** → **Absent** (different auth).
14. **What's New + Play in-app update.** → **Absent.**
15. **Live geofence coaching** while drawing a boundary ("move closer, 40m outside"). → **Absent.**
16. **Forced automatic date/time** (anti-clock-tamper as a setup gate). → **Spirit-present** (signed timestamps), no user gate.
17. **ScreenMode VIEW/EDIT** section-level edit gating. → **Not present.** *Flag: the enum name is unverified in primary; the concept (readOnly/IsEditable) is real.*

## VEIN C — Anti-fraud / integrity (fresh primary)
1. **`RequestMetadata` provenance envelope** on every capture: app/device/system/GPS + **camera FOV** + **tilt** + **blur config**. → **Partial** (we have azimuth/pitch/roll/GPS/mock; **no FOV, no blur**).
2. **Blur/sharpness capture gate** (server-tunable variance thresholds) rejecting blurry evidence. → **Missing.**
3. **Live GPS-session tracking** for the whole capture (start/update events), not one fix. → **Missing** (single fix).
4. **Geofenced capture** — warns/blocks when outside the parcel, live distance. → **Missing at capture** (we check transport distance server-side).
5. **Boundary-overlap rejection at enrollment** — anti-double-counting of land. → **Missing (zero defense).**
6. **Weight-locking on state transition** + strictly **sequential stage gating**. → **Missing.**
7. **Dual weighing** (source vs facility re-weigh) with mandatory weighbridge-slip photo. → **Missing.** *Flag: numeric reconciliation tolerance inferred, not confirmed in dex.*
8. **Mock-location detection** stamped on the record (`isFromMockProvider`). → **Parity.**
9. **Client SHA-256 in `FileMetadata`.** → **Parity+ — we ALSO Ed25519-sign the hash; they only store it.**
10. **Per-media `verification_status` + `remarks`** reviewer loop (bounce one photo with a reason). → **Missing** (we reject at sync, no per-media review).
11. **Dung-mix video end-use proof.** → **Different** (delivery/buyer record).
12. **Asset-ID-visible-in-frame** requirement + phase-timed shots. → **Partial.**
13. **One-active-cycle-per-facility** + completeness gating (anti double-logging). → **Partial.**
14. **Mobile-number uniqueness** (anti ghost-farmer). → **Missing for farmers.**
- **Where we LEAD (verified):** per-media **Ed25519 signatures** over the declared SHA-256, and **SQLCipher-encrypted** PII at rest. Varaha's evidence is **hashed but unsigned**, and its PII (names, signatures, Aadhaar, bank) is **plaintext**. Keep and market this.

## VEIN D — Sync / offline resilience (from Platform mine + RE map)
1. **Media conversion state machine** (compress images / transcode video / build PDFs / drop 0-byte) before upload. → **Missing** (we upload full-res, no compression).
2. **Presigned-S3 upload with progress 0–100.** → **Missing** (direct multipart, no progress %).
3. **4 WorkManager workers** (sync / preprocess / upload / cleanup). → **We have a custom two-phase outbox + WorkManager 15-min.**
4. **`server_id` write-back + media repointing** (`ref_local_id→ref_id`). → **We split via `json_synced_at`/`media_synced_at`.**
5. **7-state sync incl. CONFLICT + tombstone-delete + pull-reconcile.** → **We're push-only, 4-state (no conflict/pull).**
6. **Logout-with-unsynced guard + queue tied to mobile number.** → **Missing** (the logout guard).
- **Where we LEAD (verified):** **two-phase hash-verified commit** (assert `server_sha256` matches before deleting the local file), **atomic CAS row-claim** (no double-POST across loop + worker), and encrypted store.

---

## The high-IQ shortlist — smartest things worth knowing (cross-cutting, ranked)
1. **Source-parcel entity + boundary-overlap rejection** (A1 + C5) — solves the three things a verifier attacks first (provenance, additionality, double-counting). Our single biggest structural gap.
2. **Config-driven methodology/registry** (A2) — the demo→platform line; do it before more code hardcodes `CSI-3.2`.
3. **Geofenced + live-GPS capture** (C3 + C4) — move our server-side transport check to capture time; strongest presence-proof upgrade.
4. **Blur gate + framing overlay + asset-ID-in-frame** (C2, B4, C12) — cheap, no-server-ML quality/consistency controls that make evidence machine-verifiable.
5. **bulk-density volume→mass, production-gated** (A3) — auditable field mass where a scale is impossible.
6. **Pincode / IFSC auto-fill** (B1, B2) — the biggest field-error reduction, when we add KYC/payments.
7. **Consequence-explicit confirms + weight-lock-on-commit** (B8 + C6) — cheap integrity, removes "edit the number later."
8. **Media compression + upload progress** (D1, D2) — rural bandwidth + farmer trust.
9. **Per-media reviewer verdict loop** (C10) — targeted recapture instead of bulk trust.
10. **Save-to-Draft, role-switch, day-start lock** (B7, B10, B6) — operational breadth for multi-crew.

## Protect + market (our verified moat Varaha can't quickly copy)
Ed25519-signed evidence · SQLCipher encryption-at-rest · sensor-grounded burn/yield (BLE temp+weight + ATECC608B attestation) · transparent server credit engine + verifier portal · mathematical permanence (H:Corg decay). Their architecture (plaintext DB, unsigned metadata, no verifier product) cannot retrofit these in a sprint.

## Unverified-in-primary (do not assert as fact)
- Exact multi-tenancy HTTP header name (only org/tenant *scoping* proven).
- `RequestMetadata.request_id` / `SystemMetadata.network_type` fields.
- Dual-weigh numeric reconciliation tolerance.
- A named `ScreenMode.VIEW/EDIT` enum.
- Deliberate accessibility/large-touch design.
- (RE-doc-only, not re-confirmed this pass) cleartext-traffic flag; measure.sh test endpoint.
