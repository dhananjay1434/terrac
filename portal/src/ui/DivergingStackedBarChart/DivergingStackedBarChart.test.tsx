import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import DivergingStackedBarChart, { type DivergingBar } from "./DivergingStackedBarChart";

const DATA: DivergingBar[] = [
  {
    label: "Jan 2026",
    above: [{ label: "Net credit", value: 5, color: "#0a0" }],
    below: [
      { label: "Safety", value: 1, color: "#a00" },
      { label: "Transport", value: 2, color: "#a50" },
    ],
    tooltip: [
      { label: "Net credit", value: 5, bold: true },
      { label: "− Safety", value: 1 },
      { label: "− Transport", value: 2 },
    ],
  },
  {
    label: "Feb 2026",
    above: [{ label: "Net credit", value: 0, color: "#0a0" }],
    below: [
      { label: "Safety", value: 0, color: "#a00" },
      { label: "Transport", value: 0, color: "#a50" },
    ],
    tooltip: [{ label: "Net credit", value: 0, bold: true }],
  },
  {
    label: "Mar 2026",
    above: [{ label: "Net credit", value: 3, color: "#0a0" }],
    below: [{ label: "Safety", value: 1, color: "#a00" }],
    tooltip: [
      { label: "Net credit", value: 3, bold: true },
      { label: "− Safety", value: 1 },
    ],
  },
];

describe("DivergingStackedBarChart", () => {
  it("renders one segment rect per non-zero stack entry (excluding hit-areas)", () => {
    const { container } = render(<DivergingStackedBarChart data={DATA} />);
    const segmentRects = Array.from(
      container.querySelectorAll('rect:not([data-hit-area="true"])'),
    );
    // Jan: 1 above + 2 below = 3. Feb: all zero = 0. Mar: 1 above + 1 below = 2.
    expect(segmentRects.length).toBe(5);
  });

  it("still renders the x-axis label for an all-zero bar and does not drop it from the layout", () => {
    render(<DivergingStackedBarChart data={DATA} />);
    expect(screen.getByText("Feb 2026")).toBeInTheDocument();
    // All three labels present means all three bar slots exist.
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
    expect(screen.getByText("Mar 2026")).toBeInTheDocument();
  });

  it("shows a floating tooltip with the bar's rows on hover and hides it on mouse leave", () => {
    const { container } = render(<DivergingStackedBarChart data={DATA} ariaLabel="Credits" />);
    const hitAreas = container.querySelectorAll('rect[data-hit-area="true"]');
    expect(hitAreas.length).toBe(3);

    fireEvent.mouseEnter(hitAreas[0]);
    // "Jan 2026" now appears twice (x-axis label + tooltip header) — assert
    // via the tooltip-only content instead of the ambiguous shared label.
    expect(screen.getAllByText("Jan 2026").length).toBe(2);
    expect(screen.getByText("− Safety")).toBeInTheDocument();

    fireEvent.mouseLeave(hitAreas[0]);
    expect(screen.queryByText("− Safety")).not.toBeInTheDocument();
    expect(screen.getAllByText("Jan 2026").length).toBe(1);
  });

  it("shows the tooltip on focus and hides it on blur (keyboard accessible)", () => {
    const { container } = render(<DivergingStackedBarChart data={DATA} />);
    const hitAreas = container.querySelectorAll('rect[data-hit-area="true"]');
    fireEvent.focus(hitAreas[2]);
    expect(screen.getAllByText("Mar 2026").length).toBe(2);
    expect(screen.getByText("− Safety")).toBeInTheDocument();
    fireEvent.blur(hitAreas[2]);
    expect(screen.queryByText("− Safety")).not.toBeInTheDocument();
  });

  it("renders the default empty label when data is empty", () => {
    render(<DivergingStackedBarChart data={[]} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders a custom empty label when provided", () => {
    render(<DivergingStackedBarChart data={[]} emptyLabel="Nothing yet" />);
    expect(screen.getByText("Nothing yet")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<DivergingStackedBarChart data={DATA} ariaLabel="Credits over time" />);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
