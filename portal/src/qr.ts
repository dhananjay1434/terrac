// Cross-system QR payload formats. These strings are contracts read by the
// mobile app (P1-S3 kiln select, P1-S8 enrollment), so their exact shape is
// pinned by snapshot tests — do not reorder keys or change the prefix.

export interface KilnQr {
  kiln_id: string;
  kiln_type: string;
  capacity_l?: number | null;
}

export function kilnQrPayload(k: KilnQr): string {
  return (
    "dmrv-kiln:v1:" +
    JSON.stringify({
      kiln_id: k.kiln_id,
      kiln_type: k.kiln_type,
      capacity_l: k.capacity_l ?? null,
    })
  );
}

export interface EnrollQr {
  url: string;
  token: string;
}

// Mirrors the backend mint output (server-side json.dumps of {url, token}).
export function enrollQrPayload(e: EnrollQr): string {
  return "dmrv-enroll:v1:" + JSON.stringify({ url: e.url, token: e.token });
}
