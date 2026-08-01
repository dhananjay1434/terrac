// V2 portal client for the telemetry/hierarchy plane (M2.6). Kept SEPARATE from
// the frozen api.ts: this file may evolve with /api/v2 without ever touching the
// v1 contract. The 20-line fetch helper below is DELIBERATELY duplicated (not
// imported from api.ts) so api.ts stays a closed, frozen surface — the small
// copy cost buys a hard isolation boundary.
import { clearSession, getToken } from "./auth";
import type { ThermalMapData } from "./ui/ThermalMapChart/ThermalMapChart";
import type { LoadTelemetryData } from "./ui/LoadTelemetryChart/LoadTelemetryChart";

const BASE = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

export class AuthError extends Error {}

async function req<T>(path: string, opts: RequestInit = {}): Promise<T> {
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
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

// ── telemetry read (M2.3) ───────────────────────────────────────────────────
export interface TelemetryResponse {
  channels: ThermalMapData["channels"];
  burn: ThermalMapData["burn"];
}

export function getTelemetry2(
  uuid: string,
  params: { channels?: string[]; res?: "10s" | "1m" } = {},
): Promise<TelemetryResponse> {
  const q = new URLSearchParams();
  if (params.channels?.length) q.set("channels", params.channels.join(","));
  if (params.res) q.set("res", params.res);
  const s = q.toString();
  return req(`/api/v1/portal/batches/${uuid}/telemetry2${s ? `?${s}` : ""}`);
}

/** Derive the LoadTelemetryChart shape from the LOAD channel of a telemetry
 * response (null when no LOAD channel — tier-aware). */
export function loadFromTelemetry(
  t: TelemetryResponse,
): LoadTelemetryData | null {
  const load = t.channels["LOAD"];
  if (!load?.points?.length) return null;
  return { points: load.points };
}

// ── live burn stream via single-use ticket (M2.4, audit A1) ─────────────────
type StreamMsg = { type: "telemetry"; frame: unknown } | { type: "stream_closed" };

/**
 * Open a live SSE stream for a burn. EventSource cannot send an Authorization
 * header, so we first mint a single-use, 60 s, batch-bound ticket over the
 * authed POST, then open the stream with it in the query string (safe: the
 * ticket is one-shot and short-lived). On error we mint a fresh ticket and
 * reconnect up to 3× with backoff, then emit {type:"stream_closed"}.
 *
 * Returns a Promise of a disposer that closes the stream.
 */
export async function openBurnStream(
  uuid: string,
  onMsg: (m: StreamMsg) => void,
): Promise<() => void> {
  let es: EventSource | null = null;
  let attempts = 0;
  let disposed = false;

  async function mintTicket(): Promise<string> {
    const r = await req<{ ticket: string }>(
      `/api/v1/portal/streams/burn/${uuid}/ticket`,
      { method: "POST" },
    );
    return r.ticket;
  }

  async function connect(): Promise<void> {
    if (disposed) return;
    const ticket = await mintTicket();
    if (disposed) return;
    const url = `${BASE}/api/v1/portal/streams/burn/${uuid}?ticket=${encodeURIComponent(ticket)}`;
    es = new EventSource(url);
    es.addEventListener("telemetry", (ev) => {
      try {
        onMsg({ type: "telemetry", frame: JSON.parse((ev as MessageEvent).data) });
      } catch {
        /* malformed frame — skip, next frame reconciles */
      }
    });
    es.onerror = () => {
      es?.close();
      es = null;
      if (disposed) return;
      if (attempts >= 3) {
        onMsg({ type: "stream_closed" });
        return;
      }
      attempts += 1;
      setTimeout(() => void connect(), 2000);
    };
    es.onopen = () => {
      attempts = 0; // a clean open resets the backoff budget
    };
  }

  await connect();
  return () => {
    disposed = true;
    es?.close();
    es = null;
  };
}

// ── hierarchy (M1.5) ────────────────────────────────────────────────────────
export interface HierarchyNode {
  network_id: string;
  name: string;
  sites: { site_id: string; name: string; kilns: { kiln_id: string; sensor_profile: string }[] }[];
}
export function getHierarchy(): Promise<{ networks: HierarchyNode[] }> {
  return req("/api/v1/portal/hierarchy");
}

// ── ledgers (M5.1) ────────────────────────────────────────────────────────
export interface LedgerBucket {
  period: string;
  total_kg: number;
  by_species: Record<string, number>;
  batch_codes: string[];
  row_count: number;
}
export interface BiomassLedgerResponse {
  bucket: "day" | "month";
  buckets: LedgerBucket[];
  totals: {
    total_kg: number;
    by_species: Record<string, number>;
    row_count: number;
  };
}
// ── capability descriptor (STITCHING Phase B) ───────────────────────────────
import type { BatchCapabilities } from "./apiV2types";

/** Fetch the per-batch capability verdict. The portal should render panels from
 * this instead of probing endpoints and catching failures. */
export function getBatchCapabilities(uuid: string): Promise<BatchCapabilities> {
  return req(`/api/v1/portal/batches/${uuid}/capabilities`);
}

export function getBiomassLedger(params: {
  from?: string;
  to?: string;
  bucket?: "day" | "month";
  site_id?: string;
  network_id?: string;
}): Promise<BiomassLedgerResponse> {
  const q = new URLSearchParams();
  if (params.from) q.set("from", params.from);
  if (params.to) q.set("to", params.to);
  if (params.bucket) q.set("bucket", params.bucket);
  if (params.site_id) q.set("site_id", params.site_id);
  if (params.network_id) q.set("network_id", params.network_id);
  const s = q.toString();
  return req(`/api/v1/portal/ledgers/biomass${s ? `?${s}` : ""}`);
}
