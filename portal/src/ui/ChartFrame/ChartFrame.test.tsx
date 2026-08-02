import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import ChartFrame from "./ChartFrame";

function Basic() {
  return (
    <ChartFrame
      ariaLabel="test chart"
      title="Test"
      yDomain={[0, 100]}
      yTicks={[0, 50, 100]}
      legend={[{ label: "Series A", color: "var(--indigo-600)" }]}
    >
      {({ w, yScale }) => <rect x={0} y={yScale(100)} width={w} height={4} />}
    </ChartFrame>
  );
}

describe("ChartFrame", () => {
  it("renders one y-axis label per tick", () => {
    const { container } = render(<Basic />);
    const texts = Array.from(container.querySelectorAll("text")).map(
      (t) => t.textContent,
    );
    expect(texts).toContain("0");
    expect(texts).toContain("50");
    expect(texts).toContain("100");
  });

  it("renders the title and legend", () => {
    render(<Basic />);
    expect(screen.getByText("Test")).toBeInTheDocument();
    expect(screen.getByText("Series A")).toBeInTheDocument();
  });

  it("exposes the SVG with its aria-label", () => {
    render(<Basic />);
    expect(screen.getByLabelText("test chart")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<Basic />);
    expect((await axe(container)).violations).toEqual([]);
  });

  it("renders no hover overlay/crosshair when onHoverFrac is not passed", () => {
    const { container } = render(<Basic />);
    expect(container.querySelector('rect[fill="transparent"]')).toBeNull();
    expect(container.querySelector('line[data-crosshair="true"]')).toBeNull();
  });

  it("renders the hover capture rect and a crosshair when wired", () => {
    const { container } = render(
      <ChartFrame ariaLabel="hover chart" yDomain={[0, 100]} onHoverFrac={() => {}} crosshairFrac={0.5}>
        {({ w, yScale }) => <rect x={0} y={yScale(100)} width={w} height={4} />}
      </ChartFrame>,
    );
    expect(container.querySelector('rect[fill="transparent"]')).not.toBeNull();
    expect(container.querySelector('line[data-crosshair="true"]')).not.toBeNull();
  });
});
