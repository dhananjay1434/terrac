import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BatchDetail from "../BatchDetail";
import { getBatch, getBatchTimeline, type BatchDetail as Detail } from "../../api";
import { getBatchCapabilities } from "../../api2";
import type { BatchCapabilities } from "../../apiV2types";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, getBatch: vi.fn(), getBatchTimeline: vi.fn(), fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock") };
});
vi.mock("../../api2", () => ({ getBatchCapabilities: vi.fn(), getTelemetry2: vi.fn().mockRejectedValue(new Error("no v2 telemetry in this test")) }));
vi.mock("../../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../auth")>();
  return { ...actual, getRole: vi.fn(() => "verifier") };
});

const UUID = "aaaa1111-2222-3333-4444-555566667777";
function detail(): Detail {
  return {
    batch: { batch_uuid: UUID, device_id: "dev-1", project_id: "p1", status: "RECEIVED",
      provisional: false, reason_count: 0, net_credit_t_co2e: 1.2, wet_yield_kg: 100, received_at: "2026-07-01T10:00:00Z" },
    compliance: { batch_uuid: UUID, provisional: false, issuable: true, reasons: [], checklist: [] },
    media: [], lca_breakdown: [], telemetry: { min_temp: 300, max_temp: 500, temperature_readings: [] },
  } as unknown as Detail;
}
const caps = (o: Partial<BatchCapabilities> = {}): BatchCapabilities => ({ telemetry: "none", thermal: true, load: false, timeline: true, journeys: true, ledgers: true, provenance_code: false, tier: "none", ...o });
function renderAt() {
  return render(<MemoryRouter initialEntries={[`/batches/${UUID}`]}><Routes><Route path="/batches/:uuid" element={<BatchDetail />} /></Routes></MemoryRouter>);
}
describe("BatchDetail capability gating", () => {
  beforeEach(() => {
    vi.mocked(getBatch).mockResolvedValue(detail());
    vi.mocked(getBatchTimeline).mockResolvedValue([{ operation_id: "op1", label: "Received", stage: "received", ok: true, media: [] } as never]);
  });
  it("hides the custody timeline when caps.timeline is false", async () => {
    vi.mocked(getBatchCapabilities).mockResolvedValue(caps({ timeline: false }));
    renderAt(); await screen.findAllByText(/net credit/i);
    await waitFor(() => expect(screen.queryByText(/Custody timeline/i)).toBeNull());
  });
  it("shows the custody timeline when caps.timeline is true", async () => {
    vi.mocked(getBatchCapabilities).mockResolvedValue(caps({ timeline: true }));
    renderAt(); expect(await screen.findByText(/Custody timeline/i)).toBeTruthy();
  });
  it("falls back to showing the timeline when the caps probe REJECTS", async () => {
    vi.mocked(getBatchCapabilities).mockRejectedValue(new Error("boom"));
    renderAt(); expect(await screen.findByText(/Custody timeline/i)).toBeTruthy();
  });
});
