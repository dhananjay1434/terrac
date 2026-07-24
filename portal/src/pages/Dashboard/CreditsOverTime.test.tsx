import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CreditsOverTime from "./CreditsOverTime";
import type { CreditBucket } from "../../api";

const BUCKETS: CreditBucket[] = [
  { period: "2026-01", issued_credit_t_co2e: 1.5, issued_count: 1, provisional_count: 0 },
  { period: "2026-02", issued_credit_t_co2e: 0, issued_count: 0, provisional_count: 0 },
  { period: "2026-03", issued_credit_t_co2e: 2.25, issued_count: 2, provisional_count: 1 },
];

describe("CreditsOverTime", () => {
  it("renders one bar per bucket, including the zero-value month (INV-5)", () => {
    const { container } = render(
      <CreditsOverTime buckets={BUCKETS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    expect(container.querySelectorAll("rect").length).toBe(3);
    expect(screen.getByText(/Jan 2026 – Mar 2026/)).toBeInTheDocument();
  });

  it("shows the empty label when there are no buckets", () => {
    render(<CreditsOverTime buckets={[]} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("No credits issued yet")).toBeInTheDocument();
  });

  it("shows a loading skeleton and no chart while loading", () => {
    const { container } = render(
      <CreditsOverTime buckets={null} loading={true} error={false} onRetry={vi.fn()} />,
    );
    expect(container.querySelector("svg")).not.toBeInTheDocument();
  });

  it("shows an error card with a working retry button", () => {
    const onRetry = vi.fn();
    render(<CreditsOverTime buckets={null} loading={false} error={true} onRetry={onRetry} />);
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
