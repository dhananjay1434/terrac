// Capability descriptor — mirrors backend capabilities.resolve_batch_capabilities exactly.
// The portal renders panels from this stated verdict instead of guessing from failed fetches.
export interface BatchCapabilities {
  telemetry: "v2" | "legacy" | "none";
  thermal: boolean;
  load: boolean;
  timeline: boolean;
  journeys: boolean;
  ledgers: boolean;
  provenance_code: boolean;
  tier: "none" | "load" | "thermal" | "full";
}

import type { BatchRow } from "./api";

/**
 * M1.4 (hierarchy_v2): additive fields the backend now returns on batch rows.
 * They live HERE, not in the frozen `api.ts`, until the typed v2 client lands in
 * M2.6. Pages cast `BatchRow` → `BatchRowV2` once, at the render boundary.
 */
export interface BatchRowV2 extends BatchRow {
  batch_code: string | null;
  network_id: string | null;
  site_id: string | null;
}

/** M1.5 — shape of GET /api/v1/portal/hierarchy (fetched via api2.ts in M2.6). */
export interface HierarchyKiln {
  kiln_id: string;
  kiln_code: string | null;
  sensor_profile: string;
}
export interface HierarchySite {
  site_id: string;
  name: string;
  kilns: HierarchyKiln[];
}
export interface HierarchyNetwork {
  network_id: string;
  name: string;
  sites: HierarchySite[];
}
export interface HierarchyResponse {
  networks: HierarchyNetwork[];
}
