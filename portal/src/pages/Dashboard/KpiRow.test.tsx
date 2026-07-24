import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import KpiRow from "./KpiRow";
import type { CreditTimeseries } from "../../api";

const TOTALS: CreditTimeseries["totals"] = {
  issued_credit_t_co2e: 12.345,
  issued_count: 3,
  provisional_count: 2,
  provisional_credit_t_co2e: 4.5,
};

describe("KpiRow", () => {
  it("renders the four tiles with fmtCredit-formatted values", () => {
    render(<KpiRow totals={TOTALS} loading={false} error={false} onRetry={vi.fn()} />);
    expect(screen.getByText("Credits issued (tCO₂e)")).toBeInTheDocument();
    expect(screen.getByText("12.345")).toBeInTheDocument();
    expect(screen.getByText("Issued batches")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Provisional (pipeline)")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Provisional credit (tCO₂e)")).toBeInTheDocument();
    expect(screen.getByText("4.500")).toBeInTheDocument();
  });

  it("never inflates the issued hero with provisional credit (INV-3)", () => {
    render(<KpiRow totals={TOTALS} loading={false} error={false} onRetry={vi.fn()} />);
    // The hero must show exactly the issued figure, never issued+provisional.
    expect(screen.queryByText("16.845")).not.toBeInTheDocument();
    expect(screen.getByText("12.345")).toBeInTheDocument();
  });

  it("shows a no-data hint instead of a fake 0 when nothing is issued yet", () => {
    render(
      <KpiRow
        totals={{
          issued_credit_t_co2e: 0,
          issued_count: 0,
          provisional_count: 0,
          provisional_credit_t_co2e: 0,
        }}
        loading={false}
        error={false}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("No credits issued yet")).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders loading skeletons and does not render totals while loading", () => {
    const { container } = render(
      <KpiRow totals={null} loading={true} error={false} onRetry={vi.fn()} />,
    );
    expect(screen.queryByText("Credits issued (tCO₂e)")).not.toBeInTheDocument();
    expect(container.querySelectorAll('[aria-hidden="true"]').length).toBeGreaterThan(0);
  });

  it("renders an error card with a working retry button", () => {
    const onRetry = vi.fn();
    render(<KpiRow totals={null} loading={false} error={true} onRetry={onRetry} />);
    const retry = screen.getByRole("button", { name: "Retry" });
    retry.click();
    expect(onRetry).toHaveBeenCalledOnce();
  });
});
