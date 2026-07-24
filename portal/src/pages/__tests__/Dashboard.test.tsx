import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../Dashboard";
import { getCreditTimeseries } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, getCreditTimeseries: vi.fn() };
});

const mockTimeseries = vi.mocked(getCreditTimeseries);

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard page", () => {
  it("renders the Dashboard heading", () => {
    mockTimeseries.mockResolvedValue({
      bucket: "month",
      from: "2026-01-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
      buckets: [],
      totals: {
        issued_credit_t_co2e: 0,
        issued_count: 0,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    });
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("fetches credit totals on mount and renders them via KpiRow", async () => {
    mockTimeseries.mockResolvedValue({
      bucket: "month",
      from: "2026-01-01T00:00:00Z",
      to: "2026-06-01T00:00:00Z",
      buckets: [],
      totals: {
        issued_credit_t_co2e: 7.5,
        issued_count: 2,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    });
    renderPage();
    expect(await screen.findByText("7.500")).toBeInTheDocument();
  });
});
