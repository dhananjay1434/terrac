import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import LoadTelemetryChart, { type LoadTelemetryData } from "./LoadTelemetryChart";

function sample(): LoadTelemetryData {
  return {
    points: [
      [1000, 0],
      [11000, 121.6],
      [21000, 90],
      [31000, 40.9],
    ],
    biomass_kg: 121.6,
    biochar_kg: 40.9,
    last_load_kg: 16.25,
  };
}

describe("LoadTelemetryChart", () => {
  it("renders a weight polyline and a dot per load event", () => {
    const { container } = render(<LoadTelemetryChart data={sample()} />);
    expect(container.querySelector("polyline")).not.toBeNull();
    expect(container.querySelectorAll("circle")).toHaveLength(4);
  });

  it("shows biomass / biochar / last-load chips with grouped kg", () => {
    const { getByText, getAllByText } = render(<LoadTelemetryChart data={sample()} />);
    expect(getByText(/Biomass/i)).toBeInTheDocument();
    // value may also appear in an SVG <title> tooltip — assert at least the chip
    expect(getAllByText("121.6 kg").length).toBeGreaterThan(0);
    expect(getByText("Last load")).toBeInTheDocument();
    expect(getByText("16.3 kg")).toBeInTheDocument(); // fmtKg rounds to 1 dp
  });

  it("tier-aware: no LOAD points → renders null", () => {
    const { container } = render(
      <LoadTelemetryChart data={{ points: [] }} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("omits a chip whose value is absent (em-dash discipline, no fabrication)", () => {
    const { queryByText } = render(
      <LoadTelemetryChart data={{ points: [[1000, 50]], biomass_kg: 50 }} />,
    );
    expect(queryByText(/Biochar/i)).toBeNull();
    expect(queryByText(/Last load/i)).toBeNull();
  });
});
