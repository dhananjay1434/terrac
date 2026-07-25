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

  it("scales the below-zero half independently of the above-zero half", () => {
    // Net credit (100 vs 10) dwarfs the deduction (1 vs 1) in real methodology
    // data — a single shared scale would render the deduction as an
    // invisible sliver. Each half must fill its own half-height based on its
    // own max, so a below-value equal to the below-max reads as tall as an
    // above-value equal to the above-max, even though the raw numbers differ
    // by two orders of magnitude.
    const SKEWED: DivergingBar[] = [
      {
        label: "A",
        above: [{ label: "Net credit", value: 100, color: "#0a0" }],
        below: [{ label: "Safety", value: 1, color: "#a00" }],
        tooltip: [],
      },
      {
        label: "B",
        above: [{ label: "Net credit", value: 10, color: "#0a0" }],
        below: [{ label: "Safety", value: 1, color: "#a00" }],
        tooltip: [],
      },
    ];
    const { container } = render(<DivergingStackedBarChart data={SKEWED} height={240} />);
    const aboveHeights = Array.from(container.querySelectorAll('rect[data-side="above"]')).map(
      (r) => Number(r.getAttribute("height")),
    );
    const belowHeights = Array.from(container.querySelectorAll('rect[data-side="below"]')).map(
      (r) => Number(r.getAttribute("height")),
    );
    // Bar A's above segment (value 100, the above-max) towers over bar B's
    // (value 10) under a shared scale — but both below segments (value 1,
    // the below-max in both bars) render at the SAME height as each other,
    // proving the below half uses its own independent scale.
    expect(aboveHeights[0]).toBeGreaterThan(aboveHeights[1] * 5);
    expect(belowHeights[0]).toBeCloseTo(belowHeights[1], 5);
    // And that shared below height should be substantial (near-full half
    // height), not a 2px sliver dictated by the above half's scale.
    expect(belowHeights[0]).toBeGreaterThan(50);
  });

  it("gives each below-zero category its own lane so a small-but-real category isn't dwarfed by a bigger one", () => {
    // Safety margin (10) dwarfs transport (0.1) by 100x in real methodology
    // data — each category must still get its own visible lane, scaled
    // against its own max, not one shared scale dominated by safety.
    const MULTI_CATEGORY: DivergingBar[] = [
      {
        label: "A",
        above: [{ label: "Net credit", value: 50, color: "#0a0" }],
        below: [
          { label: "Safety", value: 10, color: "#a00" },
          { label: "Transport", value: 0.1, color: "#a50" },
        ],
        tooltip: [],
      },
    ];
    const { container } = render(<DivergingStackedBarChart data={MULTI_CATEGORY} height={240} />);
    const belowRects = Array.from(container.querySelectorAll('rect[data-side="below"]'));
    expect(belowRects.length).toBe(2);
    const heights = belowRects.map((r) => Number(r.getAttribute("height")));
    // Both are the sole (and thus max) occurrence of their label, so each
    // fills its own lane fully — heights should be close to equal despite
    // the 100x gap in raw value.
    expect(heights[0]).toBeCloseTo(heights[1], 5);
    expect(heights[0]).toBeGreaterThan(30);
  });

  it("never fabricates a visible segment for a category that is genuinely zero", () => {
    const ALWAYS_ZERO_CH4: DivergingBar[] = [
      {
        label: "A",
        above: [{ label: "Net credit", value: 50, color: "#0a0" }],
        below: [
          { label: "Safety", value: 5, color: "#a00" },
          { label: "CH4", value: 0, color: "#a50" },
        ],
        tooltip: [],
      },
      {
        label: "B",
        above: [{ label: "Net credit", value: 40, color: "#0a0" }],
        below: [
          { label: "Safety", value: 4, color: "#a00" },
          { label: "CH4", value: 0, color: "#a50" },
        ],
        tooltip: [],
      },
    ];
    const { container } = render(<DivergingStackedBarChart data={ALWAYS_ZERO_CH4} height={240} />);
    // 2 bars x (1 above + 1 non-zero below) = 4 segment rects total, never a
    // rect for the always-zero CH4 category regardless of lane math.
    const segmentRects = container.querySelectorAll('rect:not([data-hit-area="true"])');
    expect(segmentRects.length).toBe(4);
  });

  it("has no axe violations", async () => {
    const { container } = render(<DivergingStackedBarChart data={DATA} ariaLabel="Credits over time" />);
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
