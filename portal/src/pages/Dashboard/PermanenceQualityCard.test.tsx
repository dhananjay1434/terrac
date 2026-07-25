import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import PermanenceQualityCard from "./PermanenceQualityCard";
import type { QualityMetrics } from "../../api";

const POPULATED: QualityMetrics["permanence"] = {
  n: 4,
  excluded: 2,
  h_corg: { min: 0.2, max: 0.4, avg: 0.3 },
  permanence_pct: { min: 85, max: 98, avg: 92 },
  distribution: [
    { label: "<80%", count: 0 },
    { label: "80-90%", count: 1 },
    { label: "90-95%", count: 2 },
    { label: "95-100%", count: 1 },
  ],
};

const EMPTY: QualityMetrics["permanence"] = {
  n: 0,
  excluded: 0,
  h_corg: null,
  permanence_pct: null,
  distribution: [
    { label: "<80%", count: 0 },
    { label: "80-90%", count: 0 },
    { label: "90-95%", count: 0 },
    { label: "95-100%", count: 0 },
  ],
};

describe("PermanenceQualityCard", () => {
  it("renders stats and distribution bars when data is present", () => {
    const { container } = render(
      <PermanenceQualityCard
        data={POPULATED}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("92%")).toBeInTheDocument();
    expect(screen.getByText("0.30")).toBeInTheDocument();
    expect(container.querySelectorAll("rect").length).toBe(4);
    expect(
      screen.getByText("2 batches lack a lab H/Corg"),
    ).toBeInTheDocument();
  });

  it("renders an honest no-data message when n is 0, without a fabricated 0% tile or chart", () => {
    const { container } = render(
      <PermanenceQualityCard
        data={EMPTY}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("No lab permanence data yet")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(container.querySelectorAll("rect").length).toBe(0);
  });

  it("renders the no-data message when data is null", () => {
    const { container } = render(
      <PermanenceQualityCard
        data={null}
        loading={false}
        error={false}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText("No lab permanence data yet")).toBeInTheDocument();
    expect(container.querySelectorAll("rect").length).toBe(0);
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
    expect(screen.queryByText("92%")).not.toBeInTheDocument();
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
