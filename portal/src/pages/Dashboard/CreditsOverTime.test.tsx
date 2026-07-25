import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CreditsOverTime from "./CreditsOverTime";
import type { CreditBucket } from "../../api";

const BUCKETS: CreditBucket[] = [
  {
    period: "2026-01",
    issued_credit_t_co2e: 1.5,
    issued_count: 1,
    provisional_count: 0,
    components: {
      safety_t_co2e: 0.1,
      transport_t_co2e: 0.05,
      ch4_t_co2e: 0.02,
      gross_t_co2e: 1.67,
    },
  },
  {
    period: "2026-02",
    issued_credit_t_co2e: 0,
    issued_count: 0,
    provisional_count: 0,
    components: { safety_t_co2e: 0, transport_t_co2e: 0, ch4_t_co2e: 0, gross_t_co2e: 0 },
  },
  {
    period: "2026-03",
    issued_credit_t_co2e: 2.25,
    issued_count: 2,
    provisional_count: 1,
    components: {
      safety_t_co2e: 0.15,
      transport_t_co2e: 0.08,
      ch4_t_co2e: 0.03,
      gross_t_co2e: 2.51,
    },
  },
];

describe("CreditsOverTime", () => {
  it("renders a diverging bar per bucket, including the zero-value month (INV-5)", () => {
    render(
      <CreditsOverTime buckets={BUCKETS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    // All three month labels present means all three bar slots exist, even
    // February (a real zero month) — never silently dropped.
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
    expect(screen.getByText("Feb 2026")).toBeInTheDocument();
    expect(screen.getByText("Mar 2026")).toBeInTheDocument();
    expect(screen.getByText(/Jan 2026 – Mar 2026/)).toBeInTheDocument();
  });

  it("shows our real deduction categories in the tooltip — never BlueLayer's labels", () => {
    const { container } = render(
      <CreditsOverTime buckets={BUCKETS} loading={false} error={false} onRetry={vi.fn()} />,
    );
    const hitAreas = container.querySelectorAll('rect[data-hit-area="true"]');
    fireEvent.mouseEnter(hitAreas[0]);

    expect(screen.getByText("− Safety margin")).toBeInTheDocument();
    expect(screen.getByText("− Transport")).toBeInTheDocument();
    expect(screen.getByText("− Pyrolysis (CH₄)")).toBeInTheDocument();
    expect(screen.getByText("Gross (informational)")).toBeInTheDocument();
    expect(screen.queryByText(/E production/)).not.toBeInTheDocument();
    expect(screen.queryByText(/E biomass/)).not.toBeInTheDocument();
  });

  it("treats a bucket with no components as all-zero deductions rather than crashing", () => {
    const noComponents: CreditBucket[] = [
      { period: "2026-01", issued_credit_t_co2e: 1.0, issued_count: 1, provisional_count: 0 },
    ];
    expect(() =>
      render(
        <CreditsOverTime buckets={noComponents} loading={false} error={false} onRetry={vi.fn()} />,
      ),
    ).not.toThrow();
    expect(screen.getByText("Jan 2026")).toBeInTheDocument();
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
