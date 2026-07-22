// Typed client for the P2.1/P2.2 portal API. Attaches the bearer token, and
// raises AuthError on 401 so pages can bounce to the login screen.
import { clearSession, getToken } from "./auth";

const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export class AuthError extends Error {}
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export interface BatchRow {
  batch_uuid: string;
  device_id: string | null;
  project_id: string | null;
  status: string;
  provisional: boolean;
  reason_count: number;
  net_credit_t_co2e: number;
  wet_yield_kg: number;
  received_at: string | null;
}

export interface ChecklistItem {
  code: string;
  section: string;
  label: string;
  ok: boolean;
  enforcement: string;
}

export interface Compliance {
  batch_uuid: string;
  provisional: boolean;
  issuable: boolean;
  reasons: string[];
  checklist: ChecklistItem[];
}

export interface MediaItem {
  operation_id: string;
  filename: string | null;
  sha256_hash: string;
  uploaded_at: string | null;
  capture_type: string | null;
  capture_type_verified: boolean;
  exif_lat: number | null;
  exif_lon: number | null;
  verification_status: string | null;
  verification_remarks: string | null;
}

// --- V8 Part 4 (K): per-media reviewer verdict ---
export function verifyMedia(
  operationId: string,
  body: { status: "approved" | "rejected"; remarks?: string },
): Promise<{
  operation_id: string;
  verification_status: string | null;
  verification_remarks: string | null;
}> {
  return req(`/api/v1/portal/media/${operationId}/verify`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export interface BatchDetail {
  batch: BatchRow;
  compliance: Compliance;
  evidence_counts: Record<string, number>;
  media: MediaItem[];
}

export interface ProjectRow {
  project_id: string;
  name: string;
  registry_config_id: string | null;
  org_id: string | null;
  status: string;
  created_at: string | null;
}

export interface SourceParcel {
  parcel_uuid: string;
  project_id: string;
  name: string;
  boundary_geojson: string;
  area_m2: number;
  declared_area_acres: number | null;
  bbox_min_lat: number;
  bbox_min_lon: number;
  bbox_max_lat: number;
  bbox_max_lon: number;
  boundary_method: string;
  boundary_status: string;
  created_at: string | null;
}

export interface ParcelCreateInput {
  project_id: string;
  name: string;
  boundary_geojson: Record<string, unknown> | string;
  declared_area_acres?: number;
  parcel_uuid?: string;
  boundary_method?: string;
}

async function req<T>(
  path: string,
  opts: RequestInit = {},
): Promise<T> {
  const headers = new Headers(opts.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (opts.body && !headers.has("Content-Type"))
    headers.set("Content-Type", "application/json");

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (res.status === 401) {
    clearSession();
    throw new AuthError("unauthenticated");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON body */
    }
    throw new ApiError(
      res.status,
      typeof detail === "object" ? JSON.stringify(detail) : String(detail)
    );
  }
  return (await res.json()) as T;
}

export async function login(
  email: string,
  password: string,
): Promise<{ token: string; role: string; expires_at: string }> {
  return req("/api/v1/portal/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  try {
    await req("/api/v1/portal/logout", { method: "POST" });
  } catch {
    /* best-effort */
  } finally {
    clearSession();
  }
}

export function listBatches(params: Record<string, string> = {}): Promise<{
  batches: BatchRow[];
  next_cursor: string | null;
}> {
  const q = new URLSearchParams(params).toString();
  return req(`/api/v1/portal/batches${q ? `?${q}` : ""}`);
}

export function getBatch(uuid: string): Promise<BatchDetail> {
  return req(`/api/v1/portal/batches/${uuid}`);
}

export const getBatchDetail = getBatch;

export function getSummary(): Promise<{
  by_status: Record<string, number>;
  provisional: number;
  reasons_histogram: Record<string, number>;
}> {
  return req("/api/v1/portal/summary");
}

// --- P2.5 registry (admin) + token mint ---
export function registryPost(
  kind:
    | "kilns"
    | "operator-training"
    | "supervisor-visit"
    | "scale-calibration"
    | "annual-verification",
  body: Record<string, unknown>,
): Promise<Record<string, unknown>> {
  return req(`/api/v1/portal/registry/${kind}`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface KilnRow {
  kiln_id: string;
  kiln_type: string | null;
  material: string | null;
  weight_kg: number | null;
  lifetime_years: number | null;
}

export function listKilns(): Promise<{ kilns: KilnRow[] }> {
  return req("/api/v1/portal/registry/kilns");
}

export function listProjects(
  params: Record<string, string> = {},
): Promise<{ projects: ProjectRow[]; next_cursor: string | null }> {
  const q = new URLSearchParams(params).toString();
  return req(`/api/v1/portal/projects${q ? `?${q}` : ""}`);
}

export function createProject(body: {
  project_id: string;
  name: string;
  registry_config_id?: string;
  org_id?: string;
}): Promise<ProjectRow> {
  return req("/api/v1/portal/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function listParcels(
  projectId?: string,
  before?: string,
): Promise<{ parcels: SourceParcel[]; next_cursor: string | null }> {
  const query = new URLSearchParams();
  if (projectId) query.set("project_id", projectId);
  if (before) query.set("before", before);
  const q = query.toString();
  return req(`/api/v1/portal/parcels${q ? `?${q}` : ""}`);
}

export function createParcel(body: ParcelCreateInput): Promise<SourceParcel> {
  return req("/api/v1/portal/parcels", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// --- V8 Part 2: Farmer registry (portal read: admin + verifier) ---
export interface FarmerRow {
  farmer_uuid: string;
  project_id: string;
  first_name: string;
  last_name: string | null;
  mobile_number: string;
  village: string | null;
  kyc_status: string | null;
  consent_status: string | null;
  created_at: string | null;
}

export interface FarmerDocument {
  id: number;
  doc_type: string;
  last4: string;
  media_id: string | null;
}
export interface FarmerPayment {
  id: number;
  rail: string;
  account_holder: string | null;
  masked_account: string | null;
  ifsc_code: string | null;
  masked_upi_id: string | null;
  masked_mfs_id: string | null;
}
export interface FarmerConsent {
  id: number;
  fpic_template_id: string | null;
  signed_pdf_media_id: string | null;
  holding_photo_media_id: string | null;
  signed_at: string | null;
  exclusivity_ack: boolean;
}
export interface FarmerDetail extends FarmerRow {
  gender: string | null;
  guardian_name: string | null;
  dob: string | null;
  education: string | null;
  family_size: number | null;
  reported_area: number | null;
  signature_media_id: string | null;
  sync_status: string | null;
  documents: FarmerDocument[];
  payments: FarmerPayment[];
  consents: FarmerConsent[];
}

export function listFarmers(params: {
  project_id?: string;
  search?: string;
  page?: number;
  size?: number;
}): Promise<{ items: FarmerRow[]; total: number; page: number; size: number }> {
  const q = new URLSearchParams();
  if (params.project_id) q.set("project_id", params.project_id);
  if (params.search) q.set("search", params.search);
  if (params.page) q.set("page", String(params.page));
  if (params.size) q.set("size", String(params.size));
  const s = q.toString();
  return req(`/api/v1/portal/farmers${s ? `?${s}` : ""}`);
}

export function getFarmer(farmerUuid: string): Promise<FarmerDetail> {
  return req(`/api/v1/portal/farmers/${farmerUuid}`);
}

export function issueCredit(
  uuid: string,
): Promise<{ status: string; net_credit_t_co2e: number }> {
  return req(`/api/v1/portal/batches/${uuid}/issue`, { method: "POST" });
}

// Fetch a registry export (JSON) with the bearer token and trigger a browser
// download. The endpoint is admin-gated server-side, so the browser never holds
// the admin secret. Returns the parsed report so callers/tests can assert on it.
export async function downloadExport(
  uuid: string,
  fmt: "csi" | "rainbow",
): Promise<Record<string, unknown>> {
  const report = await req<Record<string, unknown>>(
    `/api/v1/portal/batches/${uuid}/export/${fmt}`,
  );
  const blob = new Blob([JSON.stringify(report, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `batch-${uuid}-${fmt}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
  return report;
}

export function mintToken(
  body: { expires_in_days?: number; base_url?: string } = {},
): Promise<{ token: string; expires_at: string; qr_payload: string }> {
  return req("/api/v1/portal/tokens", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function submitLabResults(
  uuid: string,
  body: Record<string, unknown>,
): Promise<{ status: string; provisional: boolean; reasons: string[] }> {
  return req(`/api/v1/portal/batches/${uuid}/lab-results`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function uploadLabCertificate(
  uuid: string,
  file: File,
): Promise<{ operation_id: string; sha256_hash: string }> {
  const form = new FormData();
  form.append("file", file);
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(
    `${BASE}/api/v1/portal/batches/${uuid}/lab-certificate`,
    { method: "POST", body: form, headers },
  );
  if (res.status === 401) {
    clearSession();
    throw new AuthError("unauthenticated");
  }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return (await res.json()) as { operation_id: string; sha256_hash: string };
}

// Authed media bytes → object URL (an <img src> cannot carry a bearer header).
export async function fetchMediaUrl(operationId: string): Promise<string> {
  const headers = new Headers();
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}/api/v1/portal/media/${operationId}`, {
    headers,
  });
  if (res.status === 401) {
    clearSession();
    throw new AuthError("unauthenticated");
  }
  if (!res.ok) throw new ApiError(res.status, res.statusText);
  return URL.createObjectURL(await res.blob());
}

// --- V8 Part 3: Facility + Dispatch (portal read + facility admin) ---
export interface FacilityRow {
  facility_uuid: string;
  name: string;
  facility_type: string;
  state: string | null;
  district: string | null;
  latitude: number | null;
  longitude: number | null;
  status: string;
  created_at: string | null;
}

export function listFacilities(params: Record<string, string> = {}): Promise<{
  facilities: FacilityRow[];
  next_cursor: string | null;
}> {
  const q = new URLSearchParams(params).toString();
  return req(`/api/v1/portal/facilities${q ? `?${q}` : ""}`);
}

export function createFacility(body: {
  facility_uuid: string;
  name: string;
  facility_type: "artisanal" | "industrial";
  state?: string;
  district?: string;
}): Promise<FacilityRow> {
  return req("/api/v1/portal/facilities", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export interface DispatchRow {
  dispatch_uuid: string;
  kind: string;
  source_ref: string | null;
  dest_facility_uuid: string | null;
  status: string;
  weight_source_kg: number | null;
  weight_facility_kg: number | null;
  weight_delta_pct: number | null;
  weight_flagged: boolean | null;
  driver_name: string | null;
  truck_number: string | null;
  device_id: string | null;
  created_at: string | null;
  received_at: string | null;
}

export function listDispatch(params: Record<string, string> = {}): Promise<{
  dispatches: DispatchRow[];
  next_cursor: string | null;
}> {
  const q = new URLSearchParams(params).toString();
  return req(`/api/v1/portal/dispatch${q ? `?${q}` : ""}`);
}
