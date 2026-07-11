// Pure helpers for the lab flow — framework-free so they're unit-tested.

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// The composite-sample card QR is `dmrv-batch:v1:<uuid>` (P1-S5). Return the
// batch uuid, or null if the scanned text isn't a valid batch card.
export function parseBatchQr(text: string): string | null {
  const prefix = "dmrv-batch:v1:";
  if (!text.startsWith(prefix)) return null;
  const uuid = text.slice(prefix.length).trim();
  return UUID_RE.test(uuid) ? uuid.toLowerCase() : null;
}

export interface LabForm {
  lab_h_corg: string;
  organic_carbon_pct: string;
  biochar_moisture_samples: string; // comma/space separated
  dry_bulk_density: string;
}

export interface LabResultsBody {
  lab_h_corg?: number;
  organic_carbon_pct?: number;
  biochar_moisture_samples?: number[];
  dry_bulk_density?: number;
}

function parseSamples(raw: string): number[] {
  return raw
    .split(/[,\s]+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)
    .map(Number);
}

// Returns { errors, body }. errors is empty when valid; body is the JSON to POST
// (only the fields the tech actually filled in).
export function validateLabForm(form: LabForm): {
  errors: string[];
  body: LabResultsBody;
} {
  const errors: string[] = [];
  const body: LabResultsBody = {};

  if (form.lab_h_corg.trim()) {
    const v = Number(form.lab_h_corg);
    if (!Number.isFinite(v) || v < 0.1 || v > 1.5)
      errors.push("H:Corg must be between 0.1 and 1.5.");
    else body.lab_h_corg = v;
  }
  if (form.organic_carbon_pct.trim()) {
    const v = Number(form.organic_carbon_pct);
    if (!Number.isFinite(v) || v <= 0 || v > 1)
      errors.push("Organic carbon must be a fraction in (0, 1].");
    else body.organic_carbon_pct = v;
  }
  if (form.biochar_moisture_samples.trim()) {
    const s = parseSamples(form.biochar_moisture_samples);
    if (s.length < 3)
      errors.push("Provide at least 3 biochar moisture samples.");
    else if (s.some((n) => !Number.isFinite(n) || n < 0 || n > 100))
      errors.push("Moisture samples must be percentages in [0, 100].");
    else body.biochar_moisture_samples = s;
  }
  if (form.dry_bulk_density.trim()) {
    const v = Number(form.dry_bulk_density);
    if (!Number.isFinite(v) || v <= 0 || v > 2000)
      errors.push("Dry bulk density must be between 0 and 2000.");
    else body.dry_bulk_density = v;
  }

  if (Object.keys(body).length === 0 && errors.length === 0)
    errors.push("Enter at least one lab result.");

  return { errors, body };
}
