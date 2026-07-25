/**
 * Human-readable labels for the machine reason-codes emitted by the backend's
 * corroboration engine (backend/corroboration.py). The chart shows the friendly
 * label; the raw code stays available as a tooltip/hint so it's still
 * copy-pasteable for logs, API filters, and support.
 *
 * Curated phrasing (not mechanical de-snaking) because each is a compliance
 * message an operator must act on — reviewed wording beats string-munging.
 * Any code not in the map falls back to `humanizeReason()` so a new backend
 * reason never renders as a broken blank; add it here when you see it.
 */
export const REASON_LABELS: Record<string, string> = {
  wet_yield_uncorroborated: "Wet yield uncorroborated",
  min_temp_uncorroborated: "Min. temperature uncorroborated",
  transport_uncorroborated: "Transport uncorroborated",
  assumed_h_corg: "H:Corg assumed (no lab)",
  assumed_corg: "Organic carbon assumed (no lab)",
  attestation_unverified: "Attestation unverified",
  insufficient_moisture_samples: "Insufficient moisture samples",
  missing_pyrolysis_photos: "Missing pyrolysis photos",
  flame_height_out_of_range: "Flame height out of range",
  missing_ignition_energy: "Missing ignition energy",
  missing_composite_sample: "Missing composite sample",
  missing_delivery_record: "Missing delivery record",
  missing_buyer_identity: "Missing buyer identity",
  feedstock_not_in_positive_list: "Feedstock not in positive list",
  production_requires_valid_density: "Production requires valid density",
  insufficient_lab_sampling: "Insufficient lab sampling",
  not_an_authorized_verifier: "Verifier not authorized",
  missing_biomass_input: "Missing biomass input",
  missing_conversion_factor: "Missing conversion factor",
  unregistered_kiln: "Unregistered kiln",
  scale_calibration_expired: "Scale calibration expired",
  missing_annual_methane: "Missing annual methane test",
  missing_pah: "Missing PAH test",
  implausible_yield_biomass_ratio: "Implausible yield/biomass ratio",
  insufficient_temp_sustain: "Insufficient temperature sustain",
  implausible_moisture_spread: "Implausible moisture spread",
};

/** Fallback: turn an unmapped snake_case code into sentence case so it's at
 * least readable ("some_new_reason" → "Some new reason"). */
export function humanizeReason(code: string): string {
  if (REASON_LABELS[code]) return REASON_LABELS[code];
  const spaced = code.replace(/_/g, " ").trim();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}
