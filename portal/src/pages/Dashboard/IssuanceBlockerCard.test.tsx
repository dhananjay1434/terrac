import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import IssuanceBlockerCard from "./IssuanceBlockerCard";

const REASONS = {
  missing_annual_methane: 3,
  scale_calibration_expired: 1,
};

describe("IssuanceBlockerCard", () => {
  it("renders one bar per reason, ranked with the most common blocker first", () => {
    const { container } = render(
      <IssuanceBlockerCard reasons={REASONS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const titles = Array.from(container.querySelectorAll("rect title")).map(
      (t) => t.textContent,
    );
    expect(container.querySelectorAll("rect").length).toBe(2);
    expect(titles[0]).toContain("missing_annual_methane");
    expect(titles[1]).toContain("scale_calibration_expired");
  });

  it("shows the no-blockers message when reasons is empty", () => {
    render(<IssuanceBlockerCard reasons={{}} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("No blockers — all batches issuable")).toBeInTheDocument();
  });

  it("shows the no-blockers message when reasons is null", () => {
    render(<IssuanceBlockerCard reasons={null} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("No blockers — all batches issuable")).toBeInTheDocument();
  });

  it("shows a loading skeleton and no chart or message while loading", () => {
    const { container } = render(
      <IssuanceBlockerCard reasons={null} loading={true} error={false} onRetry={vi.fn()} />,
    );
    expect(container.querySelector("svg")).not.toBeInTheDocument();
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
