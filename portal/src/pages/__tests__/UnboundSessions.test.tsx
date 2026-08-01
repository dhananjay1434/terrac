import { it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import UnboundSessions from "../UnboundSessions";
import { getUnboundSessions, bindSession, getDeviceSyncStatus } from "../../api2";
import { getRole } from "../../auth";
vi.mock("../../api2", () => ({ getUnboundSessions: vi.fn(), bindSession: vi.fn(), getDeviceSyncStatus: vi.fn() }));
vi.mock("../../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../auth")>();
  return { ...actual, getRole: vi.fn(() => "admin") };
});
beforeEach(() => vi.clearAllMocks());
it("lists unbound sessions and binds one", async () => {
  vi.mocked(getUnboundSessions).mockResolvedValue({ unbound_sessions: [{ session_uuid: "sess-early", device_id: "d1", started_at: "2026-07-23T09:00:00Z", chunk_count: 3 }] });
  vi.mocked(bindSession).mockResolvedValue({});
  vi.spyOn(window, "prompt").mockReturnValue("batch-42");
  render(<UnboundSessions />);
  expect(await screen.findByText("sess-ear")).toBeTruthy();
  fireEvent.click(screen.getByText("Bind to batch"));
  await waitFor(() => expect(bindSession).toHaveBeenCalledWith("sess-early", "batch-42"));
});
it("checks a device watermark", async () => {
  vi.mocked(getUnboundSessions).mockResolvedValue({ unbound_sessions: [] });
  vi.mocked(getDeviceSyncStatus).mockResolvedValue({ device_id: "d1", watermarks: [{ session_uuid: "sess-1", channel: "T1", max_seq: 5 }] });
  render(<UnboundSessions />);
  fireEvent.change(await screen.findByLabelText("device id"), { target: { value: "d1" } });
  fireEvent.click(screen.getByText("Check"));
  await waitFor(() => expect(screen.getByText(/synced through seq 5/i)).toBeTruthy());
});
it("blocks non-admins", async () => {
  vi.mocked(getRole).mockReturnValue("verifier");
  render(<UnboundSessions />);
  expect(await screen.findByText(/Admins only/i)).toBeTruthy();
});
