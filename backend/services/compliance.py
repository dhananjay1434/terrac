from jsonsafe import _safe_json
from settings import _attestation_enforced

_COMPLIANCE_CATALOG: list[tuple[str, str, str]] = [
    # (reason_code, methodology_section, human_label)
    ("missing_biomass_input", "per-run (C1)", "Biomass input amount not recorded"),
    (
        "missing_conversion_factor",
        "per-run (C1)",
        "Biomass yield-conversion factor missing",
    ),
    ("wet_yield_uncorroborated", "per-run", "Wet biochar yield not corroborated"),
    ("min_temp_uncorroborated", "per-run", "Minimum burn temperature not corroborated"),
    (
        "insufficient_moisture_samples",
        "per-run (C2)",
        "Too few photographed moisture readings",
    ),
    ("missing_pyrolysis_photos", "per-run (C3)", "Open-kiln pyrolysis photos missing"),
    (
        "flame_height_out_of_range",
        "per-run (C3)",
        "Open-kiln flame height out of range",
    ),
    ("missing_ignition_energy", "per-run (C3b)", "Closed-kiln ignition energy missing"),
    (
        "missing_composite_sample",
        "per-run (C4)",
        "Site composite pile sub-sample missing",
    ),
    ("transport_uncorroborated", "per-event", "Transport distance not corroborated"),
    ("missing_delivery_record", "per-batch (C5)", "Delivery record missing"),
    ("missing_buyer_identity", "per-batch (C5)", "Buyer/end-user identity missing"),
    ("unregistered_kiln", "project (C8)", "Kiln not in the project registry"),
    ("scale_calibration_expired", "project (C8)", "Scale calibration missing/expired"),
    ("missing_annual_methane", "annual (C9)", "Current methane measurement missing"),
    ("missing_pah", "annual (C9)", "Closed-kiln PAH measurement missing"),
    ("assumed_h_corg", "lab (C7)", "H:Corg permanence ratio not lab-measured"),
    ("assumed_corg", "lab (C7)", "Organic carbon not lab-measured"),
    ("attestation_unverified", "security", "Device attestation unverified"),
]

def compliance_view(batch) -> dict:
    """Build the C10 compliance report (ordered provisional reasons + a human
    per-item checklist) for a batch. THE single grading view — reused by the
    admin `/compliance` route and the portal read API (P2.2); never forked.
    """
    reasons = _safe_json(
        batch.provisional_reasons, context=f"provisional_reasons {batch.batch_uuid}"
    )
    if not isinstance(reasons, list):
        reasons = []
    reason_set = set(reasons)

    # T1.10: per-item enforcement provenance so a verifier can tell "checked and
    # passed" from "not applicable to this batch". 'enforced' = the gate can fire
    # for this batch; 'inert_no_linkage' = needs project/scale linkage this batch
    # lacks; 'awaiting_methodology' = code path exists but is flag-gated pending
    # Rainbow sign-off (device attestation).
    def _enforcement(code: str) -> str:
        if code == "scale_calibration_expired" and not batch.scale_id:
            return "inert_no_linkage"
        if code in ("missing_annual_methane", "missing_pah") and not batch.project_id:
            return "inert_no_linkage"
        if code == "attestation_unverified" and not _attestation_enforced():
            return "awaiting_methodology"
        return "enforced"

    checklist = [
        {
            "code": code,
            "section": section,
            "label": label,
            "ok": code not in reason_set,
            "enforcement": _enforcement(code),
        }
        for code, section, label in _COMPLIANCE_CATALOG
    ]
    return {
        "batch_uuid": str(batch.batch_uuid),
        "provisional": batch.provisional,
        "issuable": not batch.provisional,
        "reasons": reasons,
        "checklist": checklist,
    }

