import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { getUnboundSessions, bindSession, getDeviceSyncStatus } from "../api2";
import { setSession } from "../auth";
const jr = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { "Content-Type": "application/json" } });
describe("unbound + bind + sync-status clients", () => {
  beforeEach(() => { localStorage.clear(); setSession("tok", "admin"); });
  afterEach(() => vi.restoreAllMocks());
  it("lists unbound sessions", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(jr({ unbound_sessions: [] }));
    await getUnboundSessions();
    expect(String(f.mock.calls[0][0])).toContain("/api/v2/telemetry/unbound-sessions");
  });
  it("binds a session (POST batch_uuid)", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(jr({ status: "ok" }));
    await bindSession("sess-1", "batch-9");
    expect(String(f.mock.calls[0][0])).toContain("/api/v2/telemetry/sessions/sess-1/bind");
    const init = f.mock.calls[0][1] as RequestInit;
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ batch_uuid: "batch-9" });
  });
  it("reads a device watermark", async () => {
    const f = vi.spyOn(globalThis, "fetch").mockResolvedValue(jr({ device_id: "d1", watermarks: [] }));
    await getDeviceSyncStatus("d1");
    expect(String(f.mock.calls[0][0])).toContain("/api/v2/telemetry/sync-status/d1");
  });
});
