import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  AuthError,
  getTelemetry2,
  loadFromTelemetry,
  openBurnStream,
  type TelemetryResponse,
} from "./api2";

beforeEach(() => {
  localStorage.setItem("dmrv.portal.token", "test-token");
});
afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("getTelemetry2", () => {
  it("sends the bearer token and parses channels", async () => {
    const body: TelemetryResponse = {
      channels: { T1: { points: [[1, 400]], max: 400, min: 400 } },
      burn: { t_start: 1, t_end: 2 },
    };
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify(body), { status: 200 }));
    const res = await getTelemetry2("b1", { channels: ["T1"], res: "1m" });
    expect(res.channels.T1.max).toBe(400);
    const url = spy.mock.calls[0][0] as string;
    expect(url).toContain("/batches/b1/telemetry2");
    expect(url).toContain("channels=T1");
    const headers = (spy.mock.calls[0][1] as RequestInit).headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer test-token");
  });

  it("throws AuthError on 401", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 401 }));
    await expect(getTelemetry2("b1")).rejects.toBeInstanceOf(AuthError);
  });
});

describe("loadFromTelemetry", () => {
  it("returns null when no LOAD channel (tier-aware)", () => {
    expect(
      loadFromTelemetry({ channels: { T1: { points: [[1, 400]], max: 400, min: 400 } }, burn: { t_start: 1, t_end: 2 } }),
    ).toBeNull();
  });
  it("maps LOAD points through", () => {
    const r = loadFromTelemetry({
      channels: { LOAD: { points: [[1, 50]], max: 50, min: 0 } },
      burn: { t_start: 1, t_end: 2 },
    });
    expect(r?.points).toHaveLength(1);
  });
});

describe("openBurnStream (ticket flow, audit A1)", () => {
  class FakeES {
    static instances: FakeES[] = [];
    url: string;
    onerror: (() => void) | null = null;
    onopen: (() => void) | null = null;
    listeners: Record<string, (e: unknown) => void> = {};
    closed = false;
    constructor(url: string) {
      this.url = url;
      FakeES.instances.push(this);
    }
    addEventListener(t: string, fn: (e: unknown) => void) {
      this.listeners[t] = fn;
    }
    close() {
      this.closed = true;
    }
  }

  beforeEach(() => {
    FakeES.instances = [];
    // @ts-expect-error test stub
    globalThis.EventSource = FakeES;
  });

  it("mints a ticket BEFORE opening EventSource, and puts it in the URL", async () => {
    const spy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify({ ticket: "TICKET123" }), { status: 200 }));
    const dispose = await openBurnStream("b9", () => {});
    // ticket minted via authed POST
    expect(spy.mock.calls[0][0]).toContain("/streams/burn/b9/ticket");
    expect((spy.mock.calls[0][1] as RequestInit).method).toBe("POST");
    // EventSource opened with the ticket
    expect(FakeES.instances).toHaveLength(1);
    expect(FakeES.instances[0].url).toContain("ticket=TICKET123");
    dispose();
    expect(FakeES.instances[0].closed).toBe(true);
  });

  it("disposer prevents reconnection", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ ticket: "T" }), { status: 200 }),
    );
    const dispose = await openBurnStream("b9", () => {});
    dispose();
    FakeES.instances[0].onerror?.(); // error after dispose must NOT reconnect
    expect(FakeES.instances).toHaveLength(1);
  });
});
