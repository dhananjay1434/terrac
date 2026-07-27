// Typed-against-api.ts mock fixtures for the UI/UX audit capture run.
// Shapes mirror the interfaces in portal/src/api.ts exactly. Scenarios:
//   default  — rich, edge-case-laden happy data (provisional batch, weight flag,
//              failing checklist item, null fields → em-dash, long strings)
//   empty    — zero rows everywhere (exercise EmptyState)
//   overflow — hundreds of rows / long content
//   error    — handled per-route in capture.mjs (route.fulfill 500)

const HASH = "3f9a1c7e8b2d4056a1c9e7f3b6d20481f5e8c3a97b1d6042e8f3a15c7b9d02e64";
const HASH2 = "a1b2c3d4e5f60718293a4b5c6d7e8f90112233445566778899aabbccddeeff00";
const UUID1 = "9f8e7d6c-5b4a-3210-fedc-ba9876543210";

// ---- Dashboard ----
export const summary = {
  by_status: { ISSUED: 24, PROVISIONAL: 7, RECEIVED: 12, REJECTED: 2 },
  provisional: 7,
  reasons_histogram: {
    "Lab results missing (H:Corg, organic carbon)": 6,
    "End-use application not recorded": 4,
    "Pyrolysis telemetry incomplete": 3,
    "Moisture readings below 1-per-100kg threshold": 2,
    "Composite pile sample missing": 1,
  },
};

export const summaryEmpty = { by_status: {}, provisional: 0, reasons_histogram: {} };

export function creditTimeseries(bucket = "month") {
  const buckets = [];
  const base = bucket === "day" ? 30 : bucket === "week" ? 12 : 6;
  for (let i = 0; i < base; i++) {
    // week buckets are week-start dates (YYYY-MM-DD), matching formatPeriod()
    const period =
      bucket === "day"
        ? `2026-07-${String(i + 1).padStart(2, "0")}`
        : bucket === "week"
        ? `2026-0${Math.floor(i / 4) + 5}-${String((i % 4) * 7 + 1).padStart(2, "0")}`
        : `2026-${String(i + 1).padStart(2, "0")}`;
    const gross = 40 + ((i * 13) % 55);
    buckets.push({
      period,
      issued_credit_t_co2e: +(gross * 0.82).toFixed(3),
      issued_count: 2 + (i % 4),
      provisional_count: i % 3,
      components: {
        safety_t_co2e: +(gross * 0.06).toFixed(3),
        transport_t_co2e: +(gross * 0.05).toFixed(3),
        ch4_t_co2e: +(gross * 0.02).toFixed(3),
        gross_t_co2e: +gross.toFixed(3),
      },
    });
  }
  const issued = buckets.reduce((a, b) => a + b.issued_credit_t_co2e, 0);
  return {
    bucket,
    from: buckets[0].period,
    to: buckets[buckets.length - 1].period,
    buckets,
    totals: {
      issued_credit_t_co2e: +issued.toFixed(3),
      issued_count: 18,
      provisional_count: 7,
      provisional_credit_t_co2e: 12.481,
    },
  };
}

export const creditTimeseriesEmpty = (bucket = "month") => ({
  bucket,
  from: "2026-02",
  to: "2026-07",
  buckets: [],
  totals: {
    issued_credit_t_co2e: 0,
    issued_count: 0,
    provisional_count: 0,
    provisional_credit_t_co2e: 0,
  },
});

export const qualityMetrics = {
  pyrolysis: {
    n: 31,
    excluded: 2,
    threshold_c: 450,
    peak_temp_c: { min: 612, max: 704, avg: 656.3 },
    pct_above_threshold: { min: 78.2, max: 99.1, avg: 92.4 },
  },
  permanence: {
    n: 29,
    excluded: 4,
    h_corg: { min: 0.28, max: 0.46, avg: 0.34 },
    permanence_pct: { min: 70.0, max: 83.2, avg: 80.1 },
    distribution: [
      { label: "80%+", count: 22 },
      { label: "70–80%", count: 7 },
    ],
  },
};

export const qualityMetricsEmpty = {
  pyrolysis: { n: 0, excluded: 0, threshold_c: 450, peak_temp_c: null, pct_above_threshold: null },
  permanence: { n: 0, excluded: 0, h_corg: null, permanence_pct: null, distribution: [] },
};

// ---- Batches ----
function batchRow(i, over = {}) {
  const prov = i % 4 === 1;
  return {
    batch_uuid: `batch-${String(i).padStart(4, "0")}-uuid-abcdef012345`,
    device_id: i % 5 === 0 ? null : `FIELD-KILN-${String((i % 12) + 1).padStart(2, "0")}`,
    project_id: i % 3 === 0 ? null : "demo-lantana-01",
    status: prov ? "PROVISIONAL" : i % 7 === 0 ? "RECEIVED" : "ISSUED",
    provisional: prov,
    reason_count: prov ? 1 + (i % 3) : 0,
    net_credit_t_co2e: prov ? 0 : +(18 + ((i * 7) % 40)).toFixed(3),
    wet_yield_kg: +(1200 + ((i * 37) % 900)).toFixed(1),
    received_at: i % 9 === 0 ? null : `2026-0${(i % 6) + 1}-${String((i % 27) + 1).padStart(2, "0")}T10:00:00Z`,
    ...over,
  };
}

export function batches(scenario = "default") {
  if (scenario === "empty") return { batches: [], next_cursor: null };
  const n = scenario === "overflow" ? 60 : scenario === "single" ? 1 : 14;
  const rows = Array.from({ length: n }, (_, i) => batchRow(i + 1));
  return { batches: rows, next_cursor: scenario === "overflow" ? "cursor-page-2" : null };
}

// ---- Batch detail ----
export function batchDetail(scenario = "default") {
  const provisional = scenario === "provisional";
  const checklist = [
    { code: "C1", section: "Sourcing", label: "Feedstock on registry positive list", ok: true, enforcement: "hard" },
    { code: "C2", section: "Moisture", label: "≥1 photographed moisture reading per 100 kg biomass", ok: !provisional, enforcement: "hard" },
    { code: "C3", section: "Pyrolysis", label: "Peak temperature ≥ 450 °C sustained", ok: true, enforcement: "hard" },
    { code: "C4", section: "Pyrolysis", label: "Flame-curtain & quenching evidence present", ok: true, enforcement: "hard" },
    { code: "C5", section: "Yield", label: "Wet biochar yield recorded", ok: true, enforcement: "soft" },
    { code: "C6", section: "Lab", label: "H:Corg and organic-carbon measured", ok: !provisional, enforcement: "hard" },
    { code: "C7", section: "End-use", label: "Application delivery + buyer recorded", ok: true, enforcement: "hard" },
    { code: "C8", section: "Equipment", label: "Kiln registered with material & lifetime", ok: true, enforcement: "hard" },
    { code: "C9", section: "Annual", label: "Project annual methane verification current", ok: true, enforcement: "hard" },
    { code: "C10", section: "Density", label: "Bulk-density calibration on file", ok: true, enforcement: "soft" },
  ];
  const reasons = provisional
    ? ["Lab results missing (H:Corg, organic carbon)", "Moisture readings below 1-per-100kg threshold"]
    : [];
  const media = [
    mediaItem("batch_photo", HASH, { verification_status: "approved" }),
    mediaItem("flame_curtain", HASH2, { verification_status: null, exif_lat: 12.9716, exif_lon: 77.5946 }),
    mediaItem("quenching", HASH, { verification_status: "rejected", verification_remarks: "Timestamp precedes burn start — re-capture required." }),
    mediaItem("flame_height", HASH2, { capture_type_verified: false, exif_lat: null, exif_lon: null }),
    mediaItem("post_burn_mass", HASH, { filename: null, uploaded_at: null }),
  ];
  return {
    batch: batchRow(1, {
      batch_uuid: "batch-0001-uuid-abcdef012345",
      status: provisional ? "PROVISIONAL" : "ISSUED",
      provisional,
      reason_count: reasons.length,
      net_credit_t_co2e: provisional ? 0 : 42.318,
    }),
    compliance: {
      batch_uuid: "batch-0001-uuid-abcdef012345",
      provisional,
      issuable: !provisional,
      reasons,
      checklist,
    },
    evidence_counts: { batch_photo: 1, flame_curtain: 3, quenching: 2, flame_height: 1, post_burn_mass: 1 },
    media,
    telemetry: {
      temperature_readings: Array.from({ length: 60 }, (_, i) => 480 + Math.round(180 * Math.sin(i / 9) + (i % 5) * 6)),
      min_temp: 471,
      max_temp: 704,
      burn_start_timestamp: "2026-07-20T08:12:00Z",
      burn_end_timestamp: "2026-07-20T10:41:00Z",
    },
    lca_breakdown: provisional
      ? null
      : {
          dry_mass_t: 1.083,
          gross_c_sink_t_co2e: 45.9,
          cremain_t: 0.71,
          safety_deduction_kg: 2140,
          transport_penalty_kg: 980,
          ch4_penalty_kg: 462,
          net_credit_t_co2e: 42.318,
          provisional: false,
          corg_assumed: false,
        },
  };
}

function mediaItem(capture_type, sha, over = {}) {
  return {
    operation_id: `op-${capture_type}-a1b2c3d4`,
    filename: `${capture_type}.jpg`,
    sha256_hash: sha,
    uploaded_at: "2026-07-20T10:05:33Z",
    capture_type,
    capture_type_verified: true,
    exif_lat: 12.9716,
    exif_lon: 77.5946,
    verification_status: null,
    verification_remarks: null,
    ...over,
  };
}

// ---- Projects / registry / parcels ----
export function projects(scenario = "default") {
  if (scenario === "empty") return { projects: [], next_cursor: null };
  const n = scenario === "overflow" ? 40 : 6;
  const projects = Array.from({ length: n }, (_, i) => ({
    project_id: i === 0 ? "demo-lantana-01" : `proj-${String(i).padStart(3, "0")}`,
    name: i === 2 ? "Western Ghats Lantana Removal & Biochar Cooperative (Phase II)" : `Biochar Project ${i + 1}`,
    registry_config_id: i % 4 === 0 ? null : "csi-default",
    org_id: i % 2 === 0 ? "org-terracipher" : null,
    allowed_feedstocks: i === 0 ? ["Lantana_camara"] : ["Lantana_camara", "Wood_chips", "Agricultural_waste"],
    client_target: i % 3 === 0 ? null : 25 + i * 5,
    status: i % 5 === 0 ? "draft" : "active",
    created_at: `2026-0${(i % 6) + 1}-14T09:00:00Z`,
  }));
  return { projects, next_cursor: scenario === "overflow" ? "cursor-2" : null };
}

export const registryConfigs = {
  registry_configs: [
    {
      config_id: "csi-default",
      registry_name: "Carbon Standards International",
      methodology_version: "CSI-3.2",
      params: { corg_table: { Lantana_camara: 0.6, Wood_chips: 0.55, Agricultural_waste: 0.5, Default: 0.55 } },
      fpic_template_set_id: "fpic-v2",
      created_at: "2026-01-10T09:00:00Z",
    },
  ],
};

export function kilns(scenario = "default") {
  if (scenario === "empty") return { kilns: [] };
  return {
    kilns: [
      { kiln_id: "KILN-DEMO-01", kiln_type: "open", material: "steel", weight_kg: 120, lifetime_years: 10 },
      { kiln_id: "KILN-DEMO-02", kiln_type: "closed", material: null, weight_kg: null, lifetime_years: 8 },
      { kiln_id: "KILN-FIELD-14", kiln_type: "open", material: "mild steel", weight_kg: 95.5, lifetime_years: null },
    ],
  };
}

export function parcels(scenario = "default") {
  if (scenario === "empty") return { parcels: [], next_cursor: null };
  return {
    parcels: [
      {
        parcel_uuid: "parcel-0001",
        project_id: "demo-lantana-01",
        name: "North Ridge Block A",
        boundary_geojson: JSON.stringify({ type: "Polygon", coordinates: [[[77.59, 12.97], [77.60, 12.97], [77.60, 12.98], [77.59, 12.98], [77.59, 12.97]]] }),
        area_m2: 48210.5,
        declared_area_acres: 12.0,
        bbox_min_lat: 12.97, bbox_min_lon: 77.59, bbox_max_lat: 12.98, bbox_max_lon: 77.6,
        boundary_method: "walk", boundary_status: "verified", created_at: "2026-03-02T09:00:00Z",
      },
      {
        parcel_uuid: "parcel-0002",
        project_id: "demo-lantana-01",
        name: "South Valley Block",
        boundary_geojson: JSON.stringify({ type: "Polygon", coordinates: [[[77.61, 12.95], [77.62, 12.95], [77.62, 12.96], [77.61, 12.96], [77.61, 12.95]]] }),
        area_m2: 31980.0,
        declared_area_acres: null,
        bbox_min_lat: 12.95, bbox_min_lon: 77.61, bbox_max_lat: 12.96, bbox_max_lon: 77.62,
        boundary_method: "draw", boundary_status: "provisional", created_at: null,
      },
    ],
    next_cursor: null,
  };
}

// ---- Farmers ----
function farmerRow(i) {
  return {
    farmer_uuid: `farmer-${String(i).padStart(4, "0")}`,
    project_id: "demo-lantana-01",
    first_name: i === 3 ? "Lakshminarayana" : ["Asha", "Ravi", "Meena", "Suresh", "Priya"][i % 5],
    last_name: i % 6 === 0 ? null : ["Devi", "Kumar", "Bai", "Reddy"][i % 4],
    mobile_number: `+91 ${90000 + i}·····`,
    village: i % 7 === 0 ? null : ["Halli", "Kere", "Doddi", "Palya"][i % 4],
    kyc_status: i % 3 === 0 ? "pending" : "verified",
    consent_status: i % 4 === 0 ? "revoked" : "signed",
    created_at: `2026-0${(i % 6) + 1}-11T09:00:00Z`,
  };
}
export function farmers(scenario = "default") {
  if (scenario === "empty") return { items: [], total: 0, page: 1, size: 20 };
  const total = scenario === "overflow" ? 240 : 5;
  const size = 20;
  const items = Array.from({ length: Math.min(size, total) }, (_, i) => farmerRow(i + 1));
  return { items, total, page: 1, size };
}
export const farmerDetail = {
  ...farmerRow(1),
  gender: "female",
  guardian_name: null,
  dob: "1984-05-12",
  education: "secondary",
  family_size: 5,
  reported_area: 2.4,
  signature_media_id: "op-sig-a1b2",
  sync_status: "synced",
  documents: [
    { id: 1, doc_type: "aadhaar", last4: "4821", media_id: "op-doc-1" },
    { id: 2, doc_type: "pan", last4: "9F3K", media_id: null },
  ],
  payments: [
    { id: 1, rail: "bank", account_holder: "Asha Devi", masked_account: "••••••4821", ifsc_code: "SBIN0001234", masked_upi_id: null, masked_mfs_id: null },
    { id: 2, rail: "upi", account_holder: null, masked_account: null, ifsc_code: null, masked_upi_id: "asha····@okaxis", masked_mfs_id: null },
  ],
  consents: [
    { id: 1, fpic_template_id: "fpic-v2", signed_pdf_media_id: "op-consent-1", holding_photo_media_id: "op-hold-1", signed_at: "2026-03-01T09:00:00Z", exclusivity_ack: true },
  ],
};

// ---- Facilities / dispatch ----
export function facilities(scenario = "default") {
  if (scenario === "empty") return { facilities: [], next_cursor: null };
  return {
    facilities: [
      { facility_uuid: "fac-001", name: "Central Processing Hub", facility_type: "industrial", state: "Karnataka", district: "Tumkur", latitude: 13.34, longitude: 77.1, status: "active", created_at: "2026-01-05T09:00:00Z" },
      { facility_uuid: "fac-002", name: "Field Aggregation Point 7", facility_type: "artisanal", state: "Karnataka", district: null, latitude: null, longitude: null, status: "active", created_at: null },
    ],
    next_cursor: null,
  };
}
function dispatchRow(i) {
  const flagged = i % 3 === 0;
  return {
    dispatch_uuid: `disp-${String(i).padStart(4, "0")}`,
    kind: i % 2 === 0 ? "biomass" : "biochar",
    source_ref: i % 5 === 0 ? null : `batch-${String(i).padStart(4, "0")}`,
    dest_facility_uuid: "fac-001",
    status: i % 4 === 0 ? "in_transit" : "received",
    weight_source_kg: +(1000 + ((i * 31) % 500)).toFixed(1),
    weight_facility_kg: flagged ? +(1000 + ((i * 31) % 500) - 180).toFixed(1) : +(1000 + ((i * 31) % 500) - 4).toFixed(1),
    weight_delta_pct: flagged ? -14.2 : -0.4,
    weight_flagged: flagged,
    driver_name: i % 6 === 0 ? null : "R. Kumar",
    truck_number: i % 6 === 0 ? null : `KA-05-${1000 + i}`,
    device_id: `FIELD-KILN-${String((i % 12) + 1).padStart(2, "0")}`,
    created_at: `2026-07-${String((i % 27) + 1).padStart(2, "0")}T08:00:00Z`,
    received_at: i % 4 === 0 ? null : `2026-07-${String((i % 27) + 1).padStart(2, "0")}T14:00:00Z`,
  };
}
export function dispatch(scenario = "default") {
  if (scenario === "empty") return { dispatches: [], next_cursor: null };
  const n = scenario === "overflow" ? 50 : 9;
  return { dispatches: Array.from({ length: n }, (_, i) => dispatchRow(i + 1)), next_cursor: scenario === "overflow" ? "cursor-2" : null };
}

export const loginResp = { token: "mock-bearer-token", role: "admin", expires_at: "2026-07-27T10:00:00Z" };
export const mintTokenResp = { token: "TC-MINT-9F8E7D6C5B4A", expires_at: "2026-08-25T10:00:00Z", qr_payload: "https://verify.terracipher.example/t/TC-MINT-9F8E7D6C5B4A" };

// 1x1 … actually a small solid JPEG (base64) so evidence cells render a real image.
export const JPEG_B64 =
  "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAAoADwDASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD3+iiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigAooooAKKKKACiiigD//2Q==";
