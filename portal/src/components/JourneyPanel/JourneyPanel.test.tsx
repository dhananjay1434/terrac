import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import JourneyPanel, { type JourneyData } from "./JourneyPanel";

function gps(): JourneyData {
  return {
    distance_km: 9.2,
    distance_source: "gps",
    vehicle_reg: "KTWB463A",
    fuel_type: "diesel",
    emissions_kg: 1122.4,
    factor_version: "emf-v1",
    recipient: { contact_name: "Kadenge Shombo", contact_phone_masked: "••••1536" },
    manifest: [{ container: "Gunia bag", count: 4, unit_kg: 50, volume_l: null, product: "Biochar-Solid Manure" }],
    application_evidence: { count: 0 },
  };
}

describe("JourneyPanel", () => {
  it("renders journey metrics with grouped values", () => {
    const { getByText } = render(<JourneyPanel data={gps()} />);
    expect(getByText("9.2 km")).toBeInTheDocument();
    expect(getByText("KTWB463A")).toBeInTheDocument();
    expect(getByText(/1,122.4 kgCO₂e/)).toBeInTheDocument();
  });

  it("chips a GPS-traced distance (audit A7 surfaced)", () => {
    const { getByText } = render(<JourneyPanel data={gps()} />);
    expect(getByText("GPS-traced")).toBeInTheDocument();
  });

  it("chips a manual distance as 'manually entered'", () => {
    const d = gps();
    d.distance_source = "manual";
    const { getByText, queryByText } = render(<JourneyPanel data={d} />);
    expect(getByText("manually entered")).toBeInTheDocument();
    expect(queryByText("GPS-traced")).toBeNull();
  });

  it("renders the masked recipient phone (never raw)", () => {
    const { getByText } = render(<JourneyPanel data={gps()} />);
    expect(getByText(/••••1536/)).toBeInTheDocument();
  });

  it("computes manifest mass = unit × count", () => {
    const { getByText } = render(<JourneyPanel data={gps()} />);
    expect(getByText("200 kg")).toBeInTheDocument(); // 50 × 4
  });

  it("shows 'not started' when no application evidence", () => {
    const { getByText } = render(<JourneyPanel data={gps()} />);
    expect(getByText(/not started/i)).toBeInTheDocument();
  });

  it("em-dashes missing values, never fabricates", () => {
    const empty: JourneyData = {
      distance_km: null,
      distance_source: null,
      vehicle_reg: null,
      fuel_type: null,
      emissions_kg: null,
      factor_version: null,
    };
    const { getAllByText, getByText } = render(<JourneyPanel data={empty} />);
    expect(getAllByText("—").length).toBeGreaterThan(0);
    expect(getByText(/no manifest lines/i)).toBeInTheDocument();
  });

  it("keeps a route slot for the M4 stitch", () => {
    const { getByTestId } = render(<JourneyPanel data={gps()} />);
    expect(getByTestId("route-slot")).toBeInTheDocument();
  });
});
