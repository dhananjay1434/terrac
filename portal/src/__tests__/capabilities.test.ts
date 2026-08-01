import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { getBatchCapabilities } from "../api2";
import { setSession } from "../auth";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const FULL = {
  telemetry: "none",
  thermal: false,
  load: false,
  timeline: true,
  journeys: true,
  ledgers: true,
  provenance_code: false,
  tier: "none",
};

describe("getBatchCapabilities", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.restoreAllMocks());

  it("calls the capabilities endpoint for the given batch uuid", async () => {
    setSession("tok-abc", "verifier");
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(jsonResponse(FULL));

    const caps = await getBatchCapabilities("batch-123");

    expect(String(fetchMock.mock.calls[0][0])).toContain(
      "/api/v1/portal/batches/batch-123/capabilities",
    );
    expect(caps.timeline).toBe(true);
    expect(caps.tier).toBe("none");
  });

  it("returns every declared capability key", async () => {
    setSession("tok-abc", "verifier");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(jsonResponse(FULL));
    const caps = await getBatchCapabilities("b1");
    for (const key of [
      "telemetry", "thermal", "load", "timeline",
      "journeys", "ledgers", "provenance_code", "tier",
    ]) {
      expect(caps).toHaveProperty(key);
    }
  });
});
