# Compliance Gap Report — App capture vs. Rainbow methodology

**Date:** 2026-07-09 · **Method:** cross-reference of (a) the Flutter app's actual capture surface and (b) the Rainbow/CSI Global Artisan C-Sink criteria as encoded in `backend/corroboration.py` + the `_COMPLIANCE_CATALOG` + `lca_engine.py`. Code-verified, no assumptions.

> **One-line takeaway:** the app captures a strong *evidence spine* (photos hashed at source, GPS/EXIF stamped, device-signed, offline-first), but it **cannot currently drive a batch to "issuable"** — for three distinct reasons, one of which is subtle and important: **several criteria the app *does* capture are stored in a shape the server's compliance gate doesn't read.**

---

## The three kinds of gap

- **① Shape mismatch (app captures it, but the gate can't see it).** The riskiest and least obvious. The app writes the data, but into a different table/field/naming than the criterion counts.
- **② No capture UI (schema-ready, screen missing).** The DB column/table exists; there's just no screen to fill it.
- **③ External channel by design (lab / admin / project).** Correctly *not* captured on the operator's phone — comes from an accredited lab or a project admin. "Assumed/missing" here is honest, not a defect.

---

## Criterion-by-criterion

| Criterion (code) | Rainbow requires | App captures today | Gap | Class |
|---|---|---|---|---|
| **C0/C8 kiln registry** (`unregistered_kiln`) | Each kiln registered (type, material, weight, lifetime); `kiln_id` on each run | Pyrolysis telemetry has `kiln_id`/`kiln_type` fields but **the screen never sets them** (always null) | No kiln-select/QR screen; kiln_type null ⇒ all kiln-conditional gates go inert | ② |
| **C1 biomass input** (`missing_biomass_input`) | Type + amount of biomass in (direct-weigh or yield-conversion), > 0 kg | `biomass_input_kg` column exists, **nullable, never populated** (no field on any screen) | No input for biomass mass/amount | ② |
| **C1 conversion factor** (`missing_conversion_factor`) | If yield-conversion method: a conversion factor | Not captured; lives on `AnnualVerification` (admin), not wired to credit | No UI + not wired | ②/③ |
| **C2 moisture** (`insufficient_moisture_samples`) | **≥10 photographed meter readings, ≥1 per 100 kg** | Screen captures **ONE** reading + one photo, written as a single `moisture_percent` on the `biomass_sourcing` row. Server counts **`moisture_readings` rows** — the app writes **zero** of those. | **Shape mismatch: even a "complete" batch reads 0 photographed readings ⇒ always OPEN.** No add-reading loop. | **①** |
| **C3 open-kiln photos** (`missing_pyrolysis_photos`, `flame_height_out_of_range`) | Open kilns: 3 stages `{flame_curtain, quenching, flame_height}`, each hashed; flame height < 0.5 m | App captures 4 smoke photos named `smoke_0/50/90/100`; **no flame-height field**; kiln_type null | **Shape mismatch: stage names don't match the required set**, and no flame-height capture. Inert today only because kiln_type is null. | **①** + ② |
| **C3b closed-kiln ignition** (`missing_ignition_energy`) | Closed kilns: ignition energy type + amount | `ignition_energy_type/amount` columns exist, never set; no field | No UI (inert while kiln_type null) | ② |
| **C4 composite sample** (`missing_composite_sample`) | ≥1 photographed set-aside sub-sample per batch (with kiln/batch QR) | `composite_pile_samples` table + writer exist; **no screen** | No composite-sample screen | ② |
| **C5 delivery + buyer** (`missing_delivery_record`, `missing_buyer_identity`) | Delivery date/amount + buyer name & contact | `delivery_date/amount/buyer_name/contact` columns exist on end-use, **nullable, not in the UI** (end-use only captures method, tonnage, GPS, farmer photo, transport-km) | No fields for delivery record / buyer identity | ② |
| **C6 transport** (`transport_uncorroborated`) | Per-leg distance/weight/vehicle/fuel for biomass & biochar | End-use has **one** `transport_distance_km`; server uses **GPS haversine** (production→application) as the authoritative distance ⇒ this passes when GPS is present. Per-leg `transport_events` table exists but **no screen**; per-leg fuel is **audit-only** (`TRANSPORT_EVENTS_ENFORCED=False`). | Distance gate satisfiable via GPS; per-leg fuel not capturable + not enforced (awaiting Rainbow factors) | ② (non-blocking) |
| **C7 lab H:Corg / Corg** (`assumed_h_corg`, `assumed_corg`) | Elemental lab analysis (H:Corg, organic carbon) — third-party, **not device-asserted** | Not captured on phone (correct). Ingested by admin via `POST /api/v1/admin/batches/{uuid}/lab`. Until then the credit uses a conservative default (H:Corg 0.35) and stays provisional. | Needs a lab result ingested (admin), by design | ③ |
| **C8 scale calibration** (`scale_calibration_expired`) | In-date scale calibration proof | Admin-registered; batch needs a `scale_id` linkage (app never sets one) ⇒ **inert_no_linkage** | Admin/project channel; app has no scale-identity capture | ③ (② for the linkage) |
| **C8 operator training / supervisor visits** | Training + site-visit records | Tables exist; **no derive_* gate, no reason code** — data-capture-only | Not enforced at all (and no UI) | ② (unenforced) |
| **C9 annual methane** (`missing_annual_methane`) | ≥3 independent methane runs per year | Admin via `annual-verification`; batch needs `project_id` linkage ⇒ **inert_no_linkage** | Admin/annual channel | ③ |
| **C9 PAH (closed-kiln)** (`missing_pah`) | Closed kilns: PAH lab measurement per cycle | Admin; inert unless project_id **and** kiln_type=closed | Admin/annual channel | ③ |
| **Security** (`attestation_unverified`) | Play Integrity / DeviceCheck device attestation | Code path wired; flag `DMRV_ATTESTATION_ENFORCED` off ⇒ **awaiting_methodology** | Needs Google/Apple creds, then flip the flag | ③ |
| **min temp corroboration** (`min_temp_uncorroborated`) | Valid burn: telemetry with **≥60 temperature samples** | App persists the temp array (enforces only ≥1 sample). A short/virtual burn may produce **<60** samples. | **Shape/threshold mismatch risk: a real or demo burn with <60 samples fails this gate.** | **①** (risk) |

---

## What a *fully-completed field batch* can and cannot turn green **today**

Even if an operator perfectly completes all five screens right now (no lab, no project linkage, kiln_type unset):

**Would pass (green):**
- `wet_yield_uncorroborated` — yield screen ✔
- `min_temp_uncorroborated` — **only if ≥60 temp samples** were streamed (watch this)
- `transport_uncorroborated` — GPS present ✔
- `unregistered_kiln`, C3 photos, C3b ignition, `scale_calibration_expired`, `missing_annual_methane`, `missing_pah` — show **N/A / pass because they're inert** (kiln_type null, no project/scale linkage)

**Would stay OPEN (cannot be satisfied by the app as built):**
- `insufficient_moisture_samples` — **shape mismatch (①)**: app writes no `moisture_readings` rows
- `missing_biomass_input` — no UI (②)
- `missing_conversion_factor` — no UI / admin (②/③)
- `missing_composite_sample` — no screen (②)
- `missing_delivery_record`, `missing_buyer_identity` — nullable fields not in UI (②)
- `assumed_h_corg`, `assumed_corg` — need lab ingest (③, by design)

**Conclusion:** a batch **cannot currently reach `issuable`** from the field app alone. The nearest-complete demo batch will always show a handful of open items — which is honest, but means the "all green / issued" moment isn't reachable today without (a) fixing the moisture shape mismatch, (b) adding the missing capture screens, and (c) ingesting a lab result.

---

## What to build to close the *field-capturable* gaps (no code here — scoped list)

Ordered by impact on getting a batch to green. (③ items are intentionally out of the app.)

1. **Moisture: capture N photographed readings into `moisture_readings` rows** (fix the ① mismatch + add the add-reading loop). *Highest impact — it's the one that can never pass today.* — M
2. **Biomass input screen/field** (`biomass_input_kg` + method) — also unlocks the C2 dynamic threshold. — S/M
3. **Composite-sample screen** (photo + kiln/batch QR → `composite_pile_samples`). — M
4. **Delivery + buyer fields** on end-use (`delivery_date`, `delivered_amount_kg`, `buyer_name`, `buyer_contact`). — S
5. **Kiln selection** (pick/scan a registered kiln → set `kiln_id` + `kiln_type`). Unblocks C0 and makes C3/C3b/C9-PAH actually apply. — M
6. **Pyrolysis stage-name alignment + flame-height field** (map the smoke stages to `{flame_curtain, quenching, flame_height}` the gate expects, or change the gate; add flame-height input for open kilns; ignition-energy input for closed). — M
7. **Ensure ≥60 temperature samples** for a valid burn (raise the demo/real sample rate or lower the threshold with methodology sign-off). — S
8. **Transport legs screen** (per-leg `transport_events`) — only matters once Rainbow provides fuel factors and `TRANSPORT_EVENTS_ENFORCED` flips. — M (deferred)

**Out of app by design (③):** lab H:Corg/Corg (admin `/lab`), scale calibration, annual methane, PAH, operator training, supervisor visits, device-attestation credentials.

---

## Honest framing for the demo

The gaps are real but they are **not embarrassing** if framed correctly:
- The system **grades every criterion and refuses to fake completeness** — that's the trust product.
- Category ③ (lab, annual, attestation) staying open is *correct* — it shows the platform knows which evidence must come from an independent lab/verifier, not the operator.
- Category ② (missing screens) is a **roadmap of capture screens**, not a design flaw — the methodology is broader than v1's field flow.
- Category ① (moisture shape mismatch, temp-sample threshold) is the one genuine **bug to fix before claiming "field-complete"** — the app collects moisture but the gate can't see it.

For tomorrow: show the provisional verdict + checklist and say *"the system knows exactly what's still needed — delivery, lab carbon, and more moisture readings — and it will not issue a credit until they're in."* Don't promise an all-green batch from the phone today.
