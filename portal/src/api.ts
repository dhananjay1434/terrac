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
}

export interface BatchDetail {
  batch: BatchRow;
  compliance: Compliance;
  evidence_counts: Record<string, number>;
  media: MediaItem[];
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
    throw new ApiError(res.status, detail);
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
