import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { axe } from "jest-axe";
import PermanenceQualityCard from "./PermanenceQualityCard";
import type { QualityMetrics } from "../../api";

const POPULATED: QualityMetrics["permanence"] = {
  n: 4,
  excluded: 2,
  h_corg: { min: 0.2, max: 0.4, avg: 0.3 },
  permanence_pct: { min: 70, max: 82.6, avg: 79 },
  distribution: [
    { label: "<70%", count: 0 },
    { label: "70-75%", count: 1 },
    { label: "75-80%", count: 0 },
    { label: "80%+", count: 3 },
  ],
};

const EMPTY: QualityMetrics["permanence"] = {
  n: 0,
  excluded: 0,
  h_corg: null,
  permanence_pct: null,
  distribution: [
    { label: "<70%", count: 0 },
    { label: "70-75%", count: 0 },
    { label: "75-80%", count: 0 },
    { label: "80%+", count: 0 },
  ],
};

describe("PermanenceQualityCard", () => {
  it("renders stats and a durability-tier breakdown when data is present", () => {
    render(
      <PermanenceQualityCard
        data={POPULATED}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("79%")).toBeInTheDocument();
    expect(screen.getByText("0.30")).toBeInTheDocument();
    // Two-tier split (not a 4-bucket histogram): 3 top-tier, 1 lower-tier.
    const list = screen.getByRole("list", { name: /durability tier/i });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(rows[0]).toHaveTextContent("Top-tier durable (~83%)");
    expect(rows[0]).toHaveTextContent("3");
    expect(rows[1]).toHaveTextContent("Lower-tier (~70%)");
    expect(rows[1]).toHaveTextContent("1");
    expect(
      screen.getByText("2 batches lack a lab H/Corg"),
    ).toBeInTheDocument();
  });

  it("renders an honest no-data message when n is 0, without a fabricated 0% tile or chart", () => {
    render(
      <PermanenceQualityCard
        data={EMPTY}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("No lab permanence data yet")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("renders the no-data message when data is null", () => {
    render(
      <PermanenceQualityCard
        data={null}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("No lab permanence data yet")).toBeInTheDocument();
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
  });

  it("renders only a skeleton while loading", () => {
    render(
      <PermanenceQualityCard
        data={POPULATED}
        loading={true}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.queryByText("79%")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No lab permanence data yet"),
    ).not.toBeInTheDocument();
  });

  it("renders a retry button on error and calls onRetry when clicked", () => {
    const onRetry = vi.fn();
    render(
      <PermanenceQualityCard
        data={null}
        loading={false}
        error={true}
        onRetry={onRetry}
      />,
    );
    const retryButton = screen.getByText("Retry");
    fireEvent.click(retryButton);
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("has no axe violations in the populated state", async () => {
    const { container } = render(
      <PermanenceQualityCard
        data={POPULATED}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
