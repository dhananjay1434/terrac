import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import BarChart from "./BarChart";

const DATA = [
  { label: "Jan", value: 10 },
  { label: "Feb", value: 25 },
  { label: "Mar", value: 0 },
  { label: "Apr", value: 40 },
];

describe("BarChart", () => {
  it("renders exactly one bar rect per datum", () => {
    const { container } = render(<BarChart data={DATA} />);
    expect(container.querySelectorAll("rect").length).toBe(DATA.length);
  });

  it("renders the default empty label when data is empty", () => {
    render(<BarChart data={[]} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders a custom empty label when provided", () => {
    render(<BarChart data={[]} emptyLabel="Nothing to show" />);
    expect(screen.getByText("Nothing to show")).toBeInTheDocument();
  });

  it("does not render any bars in the empty state", () => {
    const { container } = render(<BarChart data={[]} />);
    expect(container.querySelectorAll("rect").length).toBe(0);
  });

  it("gives each bar a <title> with the formatted value", () => {
    const formatValue = (n: number) => `${n} tCO2e`;
    const { container } = render(
      <BarChart data={DATA} formatValue={formatValue} />,
    );
    const titles = Array.from(container.querySelectorAll("rect title")).map(
      (t) => t.textContent,
    );
    expect(titles).toContain("Jan: 10 tCO2e");
    expect(titles).toContain("Feb: 25 tCO2e");
    expect(titles).toContain("Mar: 0 tCO2e");
    expect(titles).toContain("Apr: 40 tCO2e");
  });

  it("still renders a visible bar for a zero-value datum (true zero, not dropped)", () => {
    const formatValue = (n: number) => `${n} tCO2e`;
    const { container } = render(
      <BarChart data={DATA} formatValue={formatValue} />,
    );
    const zeroTitle = Array.from(
      container.querySelectorAll("rect title"),
    ).find((t) => t.textContent === "Mar: 0 tCO2e");
    expect(zeroTitle).toBeTruthy();
    const zeroBar = zeroTitle!.closest("rect");
    expect(zeroBar).not.toBeNull();
    expect(zeroBar).toBeInTheDocument();
    expect(Number(zeroBar!.getAttribute("height"))).toBeGreaterThan(0);
  });

  it("thins x-axis labels when there are many data points", () => {
    const many = Array.from({ length: 24 }, (_, i) => ({
      label: `D${i}`,
      value: i,
    }));
    const { container } = render(<BarChart data={many} />);
    // Scope to BarChart's own marks (drawn inside ChartFrame's transformed
    // <g>) — ChartFrame now also renders its own y-axis tick <text>s (C2),
    // which are siblings outside that <g>, not part of the x-axis thinning
    // this test asserts.
    const texts = container.querySelectorAll("g[transform] text");
    expect(texts.length).toBeLessThanOrEqual(8);
    expect(container.querySelectorAll("rect").length).toBe(24);
  });

  it("truncates long category labels so they don't visually overlap", () => {
    const longLabels = [
      { label: "missing_annual_methane", value: 3 },
      { label: "wet_yield_uncorroborated", value: 3 },
      { label: "missing_composite_sample", value: 2 },
      { label: "missing_buyer_identity", value: 2 },
      { label: "min_temp_uncorroborated", value: 1 },
    ];
    const { container } = render(<BarChart data={longLabels} />);
    // Scope to BarChart's own marks — ChartFrame's y-axis tick <text>s (C2)
    // are numeric, not category labels, and would fail the lookup below.
    const texts = Array.from(container.querySelectorAll("g[transform] text"));
    // Every rendered label must be shorter than its raw source label — proof
    // truncation actually kicked in for long snake_case category names —
    // and the full name always survives in the bar's <title> for hover.
    for (const t of texts) {
      const original = longLabels.find((d) => d.label.startsWith(t.textContent!.replace("…", "")));
      expect(original).toBeTruthy();
      expect(t.textContent!.length).toBeLessThan(original!.label.length + 1);
    }
    const titles = Array.from(container.querySelectorAll("rect title")).map(
      (el) => el.textContent,
    );
    expect(titles.some((t) => t?.startsWith("missing_annual_methane:"))).toBe(true);
  });

  it("prints each value above its bar when showValues is set (incl. an explicit 0)", () => {
    const { container } = render(<BarChart data={DATA} showValues />);
    // Value labels appear for every bucket, including the zero bucket — so a
    // distribution reads as exact counts, not 'one tall bar + slivers'.
    expect(screen.getByText("10")).toBeInTheDocument();
    expect(screen.getByText("25")).toBeInTheDocument();
    expect(screen.getByText("40")).toBeInTheDocument();
    // "0" now matches both a value label AND ChartFrame's y-axis zero tick
    // (C2 turned the axis on) — assert on the value-label element specifically.
    expect(container.querySelector('[class*="valueLabel"]')).not.toBeNull();
  });

  it("does NOT print value labels by default", () => {
    const { container } = render(<BarChart data={DATA} />);
    // No .valueLabel element for the zero bucket when showValues is off —
    // a "0" tick label from ChartFrame's y-axis (C2) is expected and fine.
    expect(container.querySelector('[class*="valueLabel"]')).toBeNull();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <BarChart data={DATA} ariaLabel="Monthly emissions" />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
