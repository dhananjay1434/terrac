import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { listBatches, login, AuthError } from "../api";
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
});
