# 05 — Carbon-Credit / LCA Methodology Integrity

`backend/lca_engine.py` implements an "8-step CSI Global Artisan C-Sink"
pipeline. The code is clean, pure, and well-commented — but for a product that
*issues carbon credits*, the **scientific inputs and trust gating are unsound**.
A registry auditor would reject issuance computed this way.

---

## 🔴 LCA-1 — Credits are computed for unverified / unsigned data
Already covered in `01_SECURITY.md` SEC-3, but it belongs here too: the LCA runs
and writes `net_credit_t_co2e` regardless of HMAC verification
(`server.py:263-287`). Credit numbers must never be attached to data that hasn't
passed identity + integrity + fraud checks.

---

## 🔴 LCA-2 — The 100-year permanence factor (`H:Corg`) is hardcoded, never measured
**File:** `lca_engine.py:109-127, 198-228`

`step3_cremain` is the heart of permanence accounting. It branches on
`h_corg_ratio`, but:
- `calculate_carbon_credit` defaults `h_corg_ratio=0.35` and **`create_batch`
  never passes a real value** (`server.py:264-270`), so it is *always* 0.35.
- There is no field in `BatchPayload` for a lab-measured H:Corg, and no upload
  of lab results at all.

So every batch is credited as if it were top-tier-stable biochar
(`< 0.4` branch, ~0.826 retention). Real CSI methodology requires
**lab-derived** H:Corg per production; assuming it is exactly the issuance
fraud vector the standard exists to prevent.

---

## 🟠 LCA-3 — Methane compliance is gated on a single self-reported `min_temp`
**Files:** `lca_engine.py:153-171`, `server.py:104-116`

`step7_ch4_penalty` flips between a negligible penalty (`0.005`) and a heavy one
(`30.0`) based on `min_recorded_temp_c > 190 && moisture < 15`. The
`model_validator` *comment* says a full temperature log (≥60 samples) should be
required, but the code only rejects `0 < temp < 100` — it happily accepts a
single value like `200` with no proof it came from a real burn. The 35×
difference in CH₄ penalty hinges entirely on one number the client supplies.
The local schema *has* `temperatureReadingsJson` and `hwAttestationJson`
(`tables.dart:79-97`), but the server never receives or verifies them (those
endpoints are stubs).

---

## 🟠 LCA-4 — `gross_c_sink` is computed and silently discarded
**File:** `lca_engine.py:101-106, 224-225, 239-240`

`step2_gross_c_sink` is calculated, stored in the audit object, then **never used
in the net result** (Step 8 derives from `cremain`). It's dead intermediate math
that invites confusion about whether double-counting of the 44/12 ratio occurs.
(It does *not* double-count — `cremain` is tonnes of elemental C and Step 8
applies 44/12 once — but the unused gross term makes that hard to verify.)
Either remove it or document why it's retained for audit only.

---

## 🟡 LCA-5 — Transport penalty assumes truthful GPS distance with no plausibility bound interplay
`transport_distance_km` is a client-supplied float (`server.py:84`, capped at
20,000 km) fed straight into the penalty (`lca_engine.py:139-150`). Combined with
the self-reported GPS/mock issues (SEC-4), an artisan can minimize the transport
penalty by under-reporting distance. There's no cross-check against the captured
GPS polygon / application-field coordinates the app collects.

---

## 🟡 LCA-6 — Constants are asserted, not cited to a verifiable source/version
Values like `SAFETY_DEDUCTION_KG_PER_T = 20.0`, `TRANSPORT_FACTOR = 0.01194`,
the decay coefficients (`0.1787, -0.5337, 0.8237, -0.00997`), and per-species
`Corg` (`lca_engine.py:24-47, 109-127`) are hardcoded with comments referencing
CSI PDFs but no version pinning or test fixtures derived from the standard's own
worked examples. For audit defensibility these must be (a) versioned, (b) backed
by tests that reproduce the standard's published example calculations, and (c)
configurable per methodology version.

---

## 🟡 LCA-7 — No provenance / immutability on issued credit values
A credit number is written to `batches.net_credit_t_co2e` with no signed audit
record, no methodology-version stamp, and no recomputation guard. If constants
change, historical rows become silently inconsistent. Issued values should be
immutable, versioned, and reproducible from stored inputs.

---

## Bottom line
The LCA *code* is the most polished part of the repo, but it is fed
**unverified, partly fabricated, single-sample inputs** and runs **before trust
is established**. The math being clean does not make the credits real. Before
any feature work, the credit path needs: verified inputs only, lab-data ingest
for H:Corg, full temperature/attestation verification, methodology versioning,
and reproducibility tests against the published standard.
