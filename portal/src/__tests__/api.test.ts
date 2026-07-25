import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { listBatches, login, downloadExport, getCreditTimeseries, getQualityMetrics, AuthError } from "../api";
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

  it("getCreditTimeseries passes from/to as query params and parses the shape", async () => {
    const body = {
      bucket: "month",
      from: "2026-01-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
      buckets: [
        { period: "2026-01", issued_credit_t_co2e: 1.5, issued_count: 1, provisional_count: 0 },
      ],
      totals: {
        issued_credit_t_co2e: 1.5,
        issued_count: 1,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(body));

    const out = await getCreditTimeseries({
      from: "2026-01-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
    });

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/api/v1/portal/metrics/credit-timeseries");
    expect(url).toContain(`from=${encodeURIComponent("2026-01-01T00:00:00Z")}`);
    expect(url).toContain(`to=${encodeURIComponent("2026-06-01T00:00:00Z")}`);
    expect(out).toEqual(body);
  });

  it("getCreditTimeseries with no params sends no from/to query string", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({
        bucket: "month",
        from: "x",
        to: "y",
        buckets: [],
        totals: {
          issued_credit_t_co2e: 0,
          issued_count: 0,
          provisional_count: 0,
          provisional_credit_t_co2e: 0,
        },
      }),
    );

    await getCreditTimeseries();

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).not.toContain("from=");
    expect(url).not.toContain("to=");
  });

  it("getCreditTimeseries throws AuthError on 401", async () => {
    setSession("tok-123", "verifier");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "invalid_session" }, 401),
    );

    await expect(getCreditTimeseries()).rejects.toBeInstanceOf(AuthError);
    expect(getToken()).toBeNull();
  });

  it("getQualityMetrics calls the quality endpoint and parses the shape", async () => {
    const body = {
      pyrolysis: {
        n: 2,
        excluded: 1,
        threshold_c: 450,
        peak_temp_c: { min: 600, max: 700, avg: 650 },
        pct_above_threshold: { min: 90, max: 100, avg: 95 },
      },
      permanence: {
        n: 1,
        excluded: 0,
        h_corg: { min: 0.3, max: 0.3, avg: 0.3 },
        permanence_pct: { min: 92, max: 92, avg: 92 },
        distribution: [
          { label: "<70%", count: 0 },
          { label: "70-75%", count: 0 },
          { label: "75-80%", count: 1 },
          { label: "80%+", count: 0 },
        ],
      },
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(body));

    const out = await getQualityMetrics();

    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/v1/portal/metrics/quality",
    );
    expect(out).toEqual(body);
  });

  it("getQualityMetrics throws AuthError on 401", async () => {
    setSession("tok-123", "verifier");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      jsonResponse({ detail: "invalid_session" }, 401),
    );

    await expect(getQualityMetrics()).rejects.toBeInstanceOf(AuthError);
    expect(getToken()).toBeNull();
  });

  it("getCreditTimeseries round-trips a bucket's LCA deduction components", async () => {
    const body = {
      bucket: "month",
      from: "2026-01-01T00:00:00Z",
      to: "2026-01-31T00:00:00Z",
      buckets: [
        {
          period: "2026-01",
          issued_credit_t_co2e: 5,
          issued_count: 1,
          provisional_count: 0,
          components: {
            safety_t_co2e: 0.1,
            transport_t_co2e: 0.05,
            ch4_t_co2e: 0.02,
            gross_t_co2e: 5.17,
          },
        },
      ],
      totals: {
        issued_credit_t_co2e: 5,
        issued_count: 1,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(body));

    const out = await getCreditTimeseries();

    expect(out.buckets[0].components).toEqual(body.buckets[0].components);
  });

  it("getCreditTimeseries passes bucket param in URL", async () => {
    const body = {
      bucket: "day",
      from: "2026-01-01T00:00:00Z",
      to: "2026-01-05T00:00:00Z",
      buckets: [
        { period: "2026-01-01", issued_credit_t_co2e: 0.5, issued_count: 1, provisional_count: 0 },
        { period: "2026-01-02", issued_credit_t_co2e: 0.3, issued_count: 1, provisional_count: 0 },
      ],
      totals: {
        issued_credit_t_co2e: 0.8,
        issued_count: 2,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(body));

    await getCreditTimeseries({ bucket: "day" });

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("bucket=day");
  });

  it("getCreditTimeseries defaults to bucket=month when not provided", async () => {
    const body = {
      bucket: "month",
      from: "2026-01-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
      buckets: [],
      totals: {
        issued_credit_t_co2e: 0,
        issued_count: 0,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    };
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(body));

    await getCreditTimeseries();

    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("bucket=month");
  });
});

import { groupMedia } from "../pages/BatchDetail";
import { type MediaItem } from "../api";

describe("groupMedia", () => {
  it("groups by capture type in correct order, unclassified last", () => {
    const items: MediaItem[] = [
      { capture_type: "flame_curtain", operation_id: "op1", filename: null, sha256_hash: "1", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null, verification_status: null, verification_remarks: null },
      { capture_type: "0", operation_id: "op2", filename: null, sha256_hash: "2", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null, verification_status: null, verification_remarks: null },
      { capture_type: null, operation_id: "op3", filename: null, sha256_hash: "3", uploaded_at: null, capture_type_verified: false, exif_lat: null, exif_lon: null, verification_status: null, verification_remarks: null },
      { capture_type: "flame_curtain", operation_id: "op4", filename: null, sha256_hash: "4", uploaded_at: null, capture_type_verified: true, exif_lat: null, exif_lon: null, verification_status: null, verification_remarks: null },
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
import { STEP_TITLES } from "../pages/BatchDetail";

describe("STEP_TITLES", () => {
  it("has correct titles for keys", () => {
    expect(STEP_TITLES["0"]).toBe("Smoke opacity — 0%");
    expect(STEP_TITLES["flame_curtain"]).toBe("Burn — flame curtain");
  });
  it("covers every real smoke stage and the lab certificate", () => {
    expect(STEP_TITLES["50"]).toBe("Smoke opacity — 50%");
    expect(STEP_TITLES["90"]).toBe("Smoke opacity — 90%");
    expect(STEP_TITLES["100"]).toBe("Smoke opacity — 100%");
    expect(STEP_TITLES["smoke_50"]).toBe("Smoke opacity — 50%");
    expect(STEP_TITLES["smoke_90"]).toBe("Smoke opacity — 90%");
    expect(STEP_TITLES["lab_certificate"]).toBe("Lab certificate");
  });
});
