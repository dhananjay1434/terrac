import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../Dashboard";
import { getCreditTimeseries, getQualityMetrics, getSummary } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    getCreditTimeseries: vi.fn(),
    getQualityMetrics: vi.fn(),
    getSummary: vi.fn(),
  };
});

const mockTimeseries = vi.mocked(getCreditTimeseries);
const mockQuality = vi.mocked(getQualityMetrics);
const mockSummary = vi.mocked(getSummary);

const EMPTY_TIMESERIES = {
  bucket: "month" as const,
  from: "2026-01-01T00:00:00Z",
  to: "2026-06-01T00:00:00Z",
  buckets: [],
  totals: {
    issued_credit_t_co2e: 0,
    issued_count: 0,
    provisional_count: 0,
    provisional_credit_t_co2e: 0,
  },
};

const EMPTY_QUALITY = {
  pyrolysis: {
    n: 0,
    excluded: 0,
    threshold_c: 450,
    peak_temp_c: null,
    pct_above_threshold: null,
  },
  permanence: {
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
  },
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dashboard"]}>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard page", () => {
  it("renders the Dashboard heading", () => {
    mockTimeseries.mockResolvedValue(EMPTY_TIMESERIES);
    mockQuality.mockResolvedValue(EMPTY_QUALITY);
    mockSummary.mockResolvedValue({ by_status: {}, provisional: 0, reasons_histogram: {} });
    renderPage();
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
  });

  it("fetches credit totals on mount and renders them via KpiRow", async () => {
    mockTimeseries.mockResolvedValue({
      ...EMPTY_TIMESERIES,
      totals: {
        issued_credit_t_co2e: 7.5,
        issued_count: 2,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    });
    mockQuality.mockResolvedValue(EMPTY_QUALITY);
    mockSummary.mockResolvedValue({ by_status: {}, provisional: 0, reasons_histogram: {} });
    renderPage();
    expect(await screen.findByText("7.500")).toBeInTheDocument();
  });

  it("requests a ~6-month window, not the backend's full 12-month default", async () => {
    mockTimeseries.mockResolvedValue(EMPTY_TIMESERIES);
    mockQuality.mockResolvedValue(EMPTY_QUALITY);
    mockSummary.mockResolvedValue({ by_status: {}, provisional: 0, reasons_histogram: {} });
    renderPage();

    await screen.findByRole("heading", { name: "Dashboard" });
    // This file doesn't reset mocks between tests, so check the LAST call
    // rather than assuming a call count.
    const calls = mockTimeseries.mock.calls;
    const lastCall = calls[calls.length - 1];
    expect(lastCall).toBeDefined();
    const [params] = lastCall;
    const from = new Date(params!.from!);
    const to = new Date(params!.to!);
    const monthsSpan =
      (to.getFullYear() - from.getFullYear()) * 12 + (to.getMonth() - from.getMonth());
    expect(monthsSpan).toBe(6);
  });

  it("renders the Batch Quality & Operations section alongside the credit KPIs", async () => {
    mockTimeseries.mockResolvedValue({
      ...EMPTY_TIMESERIES,
      totals: {
        issued_credit_t_co2e: 3.0,
        issued_count: 1,
        provisional_count: 0,
        provisional_credit_t_co2e: 0,
      },
    });
    mockQuality.mockResolvedValue(EMPTY_QUALITY);
    mockSummary.mockResolvedValue({
      by_status: {},
      provisional: 1,
      reasons_histogram: { missing_annual_methane: 2 },
    });
    renderPage();

    expect(
      screen.getByRole("heading", { name: "Batch Quality & Operations" }),
    ).toBeInTheDocument();
    // Existing credit KPIs still render (regression) alongside the new section.
    expect(await screen.findByText("3.000")).toBeInTheDocument();
    expect(screen.getByText("Pyrolysis quality")).toBeInTheDocument();
    expect(screen.getByText("Permanence quality")).toBeInTheDocument();
    expect(await screen.findByText("What's blocking issuance")).toBeInTheDocument();
  });
});
