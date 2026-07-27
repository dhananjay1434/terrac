import { describe, it, expect, vi, afterEach } from "vitest";
import { render, waitFor } from "@testing-library/react";
import BurnTelemetryChart from "./BurnTelemetryChart";

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe("BurnTelemetryChart (M2 stitch, graceful fallback)", () => {
  it("falls back to the legacy chart when the v2 endpoint 404s (pre-M2.3)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 404 }));
    const { container } = render(
      <BurnTelemetryChart uuid="b1" legacyReadings={[600, 650, 700]} legacyMin={600} legacyMax={700} />,
    );
    // legacy TemperatureChart renders a polyline immediately; no crash on 404
    await waitFor(() => expect(container.querySelector("polyline")).not.toBeNull());
  });

  it("adopts the v2 live view when channels come back", async () => {
    localStorage.setItem("dmrv.portal.token", "t");
    const body = {
      channels: { T1: { points: [[1000, 400], [11000, 470]], max: 470, min: 400 } },
      burn: { t_start: 1000, t_end: 11000 },
    };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(body), { status: 200 }),
    );
    const { container, getByText } = render(
      <BurnTelemetryChart uuid="b1" legacyReadings={[]} legacyMin={null} legacyMax={null} gateSatisfied />,
    );
    await waitFor(() => expect(getByText(/MAX/)).toBeInTheDocument()); // BurnLiveView/ThermalMap adopted
    expect(container.querySelector("polyline")).not.toBeNull();
  });

  it("keeps the legacy chart when v2 returns empty channels (tier-0 kiln)", async () => {
    localStorage.setItem("dmrv.portal.token", "t");
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ channels: {}, burn: { t_start: 0, t_end: 0 } }), { status: 200 }),
    );
    const { container, queryByText } = render(
      <BurnTelemetryChart uuid="b1" legacyReadings={[600, 650]} legacyMin={600} legacyMax={650} />,
    );
    await waitFor(() => expect(container.querySelector("polyline")).not.toBeNull());
    expect(queryByText(/MAX/)).toBeNull(); // did not adopt v2
  });
});
