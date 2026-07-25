import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import PyrolysisQualityCard from "./PyrolysisQualityCard";
import type { QualityMetrics } from "../../api";

const DATA: QualityMetrics["pyrolysis"] = {
  n: 3,
  excluded: 1,
  threshold_c: 450,
  peak_temp_c: { min: 600, max: 680, avg: 640 },
  pct_above_threshold: { min: 85, max: 100, avg: 95 },
};

describe("PyrolysisQualityCard", () => {
  it("renders peak temp and burn-threshold tiles plus the excluded note", () => {
    render(
      <PyrolysisQualityCard data={DATA} loading={false} error={false} onRetry={vi.fn()} />,
    );
    expect(screen.getByText("640")).toBeInTheDocument();
    expect(screen.getByText("95%")).toBeInTheDocument();
    expect(screen.getByText("1 batches lack telemetry")).toBeInTheDocument();
  });

  it("shows insufficient-data message with no fabricated 0 when n is 0", () => {
    render(
      <PyrolysisQualityCard
        data={{ n: 0, excluded: 0, threshold_c: 450, peak_temp_c: null, pct_above_threshold: null }}
        loading={false}
        error={false}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("Insufficient telemetry yet")).toBeInTheDocument();
    expect(screen.queryByText("0°C")).not.toBeInTheDocument();
  });

  it("treats null data the same as insufficient", () => {
    render(<PyrolysisQualityCard data={null} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("Insufficient telemetry yet")).toBeInTheDocument();
  });

  it("shows only the skeleton while loading", () => {
    render(<PyrolysisQualityCard data={DATA} loading={true} error={false} onRetry={vi.fn()} />);
    expect(screen.queryByText("640")).not.toBeInTheDocument();
    expect(screen.queryByText("Insufficient telemetry yet")).not.toBeInTheDocument();
  });

  it("shows a working retry button on error", () => {
    const onRetry = vi.fn();
    render(<PyrolysisQualityCard data={null} loading={false} error={true} onRetry={onRetry} />);
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("has no accessibility violations", async () => {
    const { container } = render(
      <PyrolysisQualityCard data={DATA} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
