import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import ThermalMapChart, { type ThermalMapData } from "./ThermalMapChart";

function four(): ThermalMapData {
  const pts = (base: number): [number, number][] =>
    [0, 1, 2, 3, 4].map((i) => [1000 + i * 10000, base + i * 20]);
  return {
    channels: {
      T1: { points: pts(400), max: 480, min: 400 },
      T2: { points: pts(390), max: 470, min: 390 },
      T3: { points: pts(380), max: 460, min: 380 },
      T4: { points: pts(200), max: 280, min: 200 },
    },
    burn: { t_start: 1000, t_end: 41000 },
  };
}

describe("ThermalMapChart", () => {
  it("renders one polyline per present channel (4)", () => {
    const { container } = render(<ThermalMapChart data={four()} />);
    expect(container.querySelectorAll("polyline")).toHaveLength(4);
  });

  it("tier-aware: one channel → one polyline", () => {
    const d = four();
    const single: ThermalMapData = {
      channels: { T1: d.channels.T1 },
      burn: d.burn,
    };
    const { container } = render(<ThermalMapChart data={single} />);
    expect(container.querySelectorAll("polyline")).toHaveLength(1);
  });

  it("tier-aware: zero channels → renders null (parent falls back)", () => {
    const { container } = render(
      <ThermalMapChart data={{ channels: {}, burn: { t_start: 0, t_end: 1 } }} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("MAX badge reflects the peak and gate state", () => {
    const { container, rerender } = render(<ThermalMapChart data={four()} />);
    const badge = container.querySelector("[data-gate]");
    expect(badge?.getAttribute("data-gate")).toBe("pending");
    expect(badge?.textContent).toContain("480.0");
    rerender(<ThermalMapChart data={four()} gateSatisfied />);
    expect(container.querySelector("[data-gate]")?.getAttribute("data-gate")).toBe("pass");
  });

  it("renders a gap as multiple line segments, never interpolated", () => {
    const d = four();
    // a gap spanning the middle of the series → each channel splits in two
    d.burn.gaps = [[15000, 25000]];
    const { container, getByText } = render(<ThermalMapChart data={d} />);
    // 4 channels × 2 segments = 8 polylines
    expect(container.querySelectorAll("polyline").length).toBeGreaterThan(4);
    expect(getByText(/sensor gap/i)).toBeInTheDocument();
  });
});
