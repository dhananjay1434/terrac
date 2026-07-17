import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { listBatches, login, downloadExport, AuthError } from "../api";
import { setSession, getToken } from "../auth";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("attaches the bearer token to authed requests", async () => {
    setSession("tok-123", "verifier");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse({ batches: [], next_cursor: null }));

    await listBatches({ status: "RECEIVED" });

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer tok-123");
    expect(String(fetchMock.mock.calls[0][0])).toContain("status=RECEIVED");
  });

  it("clears the session and throws AuthError on 401", async () => {
    setSession("tok-123", "verifier");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "invalid_session" }, 401),
    );

    await expect(listBatches()).rejects.toBeInstanceOf(AuthError);
    expect(getToken()).toBeNull();
  });

  it("login posts credentials and returns the token", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ token: "t", role: "admin", expires_at: "x" }),
    );
    const r = await login("a@b.c", "pw");
    expect(r.token).toBe("t");
    expect(r.role).toBe("admin");
  });

  it("downloadExport hits the portal export route and triggers a download", async () => {
    setSession("tok-123", "admin");
    const report = { batch_uuid: "u1", standard: "CSI GlobalCSinkVerificationReport v1" };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(report));
    // jsdom lacks URL.createObjectURL/revokeObjectURL — stub them.
    URL.createObjectURL = vi.fn().mockReturnValue("blob:mock");
    URL.revokeObjectURL = vi.fn();
    const createObjURL = URL.createObjectURL;
    const revokeObjURL = URL.revokeObjectURL;
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => {});

    const out = await downloadExport("u1", "csi");

    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/v1/portal/batches/u1/export/csi",
    );
    expect(out).toEqual(report);
    expect(createObjURL).toHaveBeenCalledOnce();
    expect(clickSpy).toHaveBeenCalledOnce();
    expect(revokeObjURL).toHaveBeenCalledOnce();
  });
});

import { groupMedia } from "../pages/BatchDetail";
import { type MediaItem } from "../api";

describe("groupMedia", () => {
  it("groups by capture type in correct order, unclassified last", () => {
    const items: MediaItem[] = [
      { capture_type: "flame_curtain", operation_id: "op1", filename: null, sha256_hash: "1", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null },
      { capture_type: "0", operation_id: "op2", filename: null, sha256_hash: "2", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null },
      { capture_type: null, operation_id: "op3", filename: null, sha256_hash: "3", uploaded_at: null, capture_type_verified: false, exif_lat: null, exif_lon: null },
      { capture_type: "flame_curtain", operation_id: "op4", filename: null, sha256_hash: "4", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null },
    ];
    const grouped = groupMedia(items);
    expect(grouped.length).toBe(3);
    
    expect(grouped[0][0]).toBe("flame_curtain");
    expect(grouped[0][1][0].operation_id).toBe("op1");
    expect(grouped[0][1][1].operation_id).toBe("op4");

    expect(grouped[1][0]).toBe("0");
    expect(grouped[1][1][0].operation_id).toBe("op2");

    expect(grouped[2][0]).toBe("__unclassified__");
    expect(grouped[2][1][0].operation_id).toBe("op3");
  });
});
