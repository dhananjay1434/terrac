import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import TemperatureChart from "./TemperatureChart";

describe("TemperatureChart", () => {
  it("renders a polyline for two or more readings", () => {
    const { container } = render(
      <TemperatureChart readings={[600, 650, 700]} minTemp={600} maxTemp={700} />,
    );
    expect(container.querySelector("polyline")).not.toBeNull();
  });

  it("renders an empty state for no readings, never crashes", () => {
    render(<TemperatureChart readings={[]} minTemp={null} maxTemp={null} />);
    expect(
      screen.getByText(/No thermocouple telemetry for this batch/i),
    ).toBeInTheDocument();
  });

  it("does not crash for a single reading (renders a dot, not a polyline)", () => {
    const { container } = render(
      <TemperatureChart readings={[650]} minTemp={650} maxTemp={650} />,
    );
    expect(container.querySelector("circle")).not.toBeNull();
    expect(container.querySelector("polyline")).toBeNull();
  });

  it("does not divide by zero when all readings are equal", () => {
    const { container } = render(
      <TemperatureChart readings={[650, 650, 650]} minTemp={650} maxTemp={650} />,
    );
    const poly = container.querySelector("polyline");
    expect(poly).not.toBeNull();
    const points = poly!.getAttribute("points") ?? "";
    expect(points).not.toMatch(/NaN/);
  });
});
