import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { axe } from "jest-axe";
import IssuanceBlockerCard from "./IssuanceBlockerCard";

const REASONS = {
  missing_annual_methane: 3,
  scale_calibration_expired: 1,
};

describe("IssuanceBlockerCard", () => {
  it("renders one row per reason with HUMANIZED labels, ranked most-common first", () => {
    render(
      <IssuanceBlockerCard reasons={REASONS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const list = screen.getByRole("list", { name: /issuance blockers/i });
    const rows = within(list).getAllByRole("listitem");
    expect(rows).toHaveLength(2);

    // Raw codes are humanized for display (not shown verbatim).
    expect(within(rows[0]).getByText("Missing annual methane test")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Scale calibration expired")).toBeInTheDocument();
    expect(screen.queryByText("missing_annual_methane")).not.toBeInTheDocument();

    // Counts are visible directly (not hidden in a hover tooltip).
    expect(within(rows[0]).getByText("3")).toBeInTheDocument();
    expect(within(rows[1]).getByText("1")).toBeInTheDocument();

    // Descending order: the 3-count blocker comes first.
    expect(rows[0]).toHaveTextContent("Missing annual methane test");
  });

  it("keeps the raw code available as a hover hint (title) for logs/API", () => {
    render(
      <IssuanceBlockerCard reasons={REASONS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const row = document.querySelector('[title="missing_annual_methane"]');
    expect(row).not.toBeNull();
  });

  it("shows the no-blockers message when reasons is empty", () => {
    render(<IssuanceBlockerCard reasons={{}} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("No blockers — all batches issuable")).toBeInTheDocument();
  });

  it("shows the no-blockers message when reasons is null", () => {
    render(<IssuanceBlockerCard reasons={null} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("No blockers — all batches issuable")).toBeInTheDocument();
  });

  it("shows a loading skeleton and no list or message while loading", () => {
    render(
      <IssuanceBlockerCard reasons={null} loading={true} error={false} onRetry={vi.fn()} />,
    );
    expect(screen.queryByRole("list")).not.toBeInTheDocument();
    expect(
      screen.queryByText("No blockers — all batches issuable"),
    ).not.toBeInTheDocument();
  });

  it("shows an error card with a working retry button", () => {
    const onRetry = vi.fn();
    render(
      <IssuanceBlockerCard reasons={null} loading={false} error={true} onRetry={onRetry} />,
    );
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <IssuanceBlockerCard reasons={REASONS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
