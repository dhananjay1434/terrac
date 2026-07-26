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
