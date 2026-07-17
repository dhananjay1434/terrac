import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";
import Batches from "../Batches";
import { listBatches, getSummary, AuthError, type BatchRow } from "../../api";

const mockNav = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNav };
});
vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, listBatches: vi.fn(), getSummary: vi.fn() };
});

const mockList = vi.mocked(listBatches);
const mockSummary = vi.mocked(getSummary);

const FIXTURE: BatchRow[] = [
  {
    batch_uuid: "aaaa1111-2222-3333-4444-555566667777",
    device_id: "dev-1",
    project_id: "p1",
    status: "RECEIVED",
    provisional: false,
    reason_count: 0,
    net_credit_t_co2e: 1.234,
    wet_yield_kg: 100,
    received_at: "2026-07-01T10:00:00Z",
  },
  {
    batch_uuid: "bbbb1111-2222-3333-4444-555566667777",
    device_id: "dev-2",
    project_id: "p1",
    status: "RECEIVED",
    provisional: true,
    reason_count: 2,
    net_credit_t_co2e: 0.5,
    wet_yield_kg: 40,
    received_at: "2026-07-02T10:00:00Z",
  },
];

function renderPage(path = "/batches") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Tooltip.Provider>
        <Batches />
      </Tooltip.Provider>
    </MemoryRouter>,
  );
}

describe("Batches page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ batches: FIXTURE, next_cursor: null });
    mockSummary.mockResolvedValue({
      by_status: {},
      provisional: 0,
      reasons_histogram: {},
    });
  });

  it("renders skeleton rows on initial load", () => {
    mockList.mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
  });

  it("renders the empty state when the API returns nothing", async () => {
    mockList.mockResolvedValue({ batches: [], next_cursor: null });
    renderPage();
    expect(await screen.findByText("No batches found")).toBeInTheDocument();
  });

  it("renders StatusDot variants from row eligibility", async () => {
    const { container } = renderPage();
    await screen.findByText("dev-1");
    expect(container.querySelector('[data-variant="success"]')).not.toBeNull();
    expect(container.querySelector('[data-variant="warning"]')).not.toBeNull();
  });

  it("navigates to the batch on row click", async () => {
    renderPage();
    fireEvent.click(await screen.findByText("dev-1"));
    expect(mockNav).toHaveBeenCalledWith(
      "/batches/aaaa1111-2222-3333-4444-555566667777",
    );
  });

  it("changing a filter triggers a new listBatches call with correct args", async () => {
    renderPage();
    await screen.findByText("dev-1");
    fireEvent.change(screen.getByLabelText("Filter by status"), {
      target: { value: "ISSUED" },
    });
    await waitFor(() => {
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "ISSUED", limit: "50" }),
      );
    });
  });

  it("copy button copies the full batch uuid", async () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    renderPage();
    await screen.findByText("dev-1");
    fireEvent.click(screen.getAllByRole("button", { name: "Copy batch id" })[0]);
    expect(writeText).toHaveBeenCalledWith(
      "aaaa1111-2222-3333-4444-555566667777",
    );
    expect(mockNav).not.toHaveBeenCalledWith(
      "/batches/aaaa1111-2222-3333-4444-555566667777",
    );
  });

  it("blocking issues view filters to rows with blockers", async () => {
    renderPage();
    await screen.findByText("dev-1");
    const tab = screen.getByRole("tab", { name: "Blocking issues" });
    fireEvent.mouseDown(tab, { button: 0 });
    fireEvent.click(tab);
    await waitFor(() => {
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ provisional: "true" }),
      );
    });
    await screen.findByText("dev-2");
    expect(screen.queryByText("dev-1")).not.toBeInTheDocument();
  });

  it("redirects to /login on AuthError", async () => {
    mockList.mockRejectedValue(new AuthError("unauthenticated"));
    renderPage();
    await waitFor(() => {
      expect(mockNav).toHaveBeenCalledWith("/login");
    });
  });

  it("never highlights a tab that contradicts the active select", async () => {
    renderPage();
    await screen.findByText("dev-1");

    // Select the "Issued" tab (sets status=ISSUED via the tab).
    const issuedTab = screen.getByRole("tab", { name: "Issued" });
    fireEvent.mouseDown(issuedTab, { button: 0 });
    fireEvent.click(issuedTab);
    await waitFor(() => {
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "ISSUED" }),
      );
    });
    expect(issuedTab.getAttribute("aria-selected")).toBe("true");

    // Now diverge via the eligibility select — ISSUED + provisional=true
    // matches no saved view combo, so no tab should read as selected.
    fireEvent.change(screen.getByLabelText("Filter by eligibility"), {
      target: { value: "true" },
    });
    await waitFor(() => {
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "ISSUED", provisional: "true" }),
      );
    });
    for (const tab of screen.getAllByRole("tab")) {
      expect(tab.getAttribute("aria-selected")).toBe("false");
    }
  });

  it("empty-while-filtered copy differs from empty-global, and warns when more pages exist", async () => {
    mockList.mockResolvedValue({
      batches: FIXTURE,
      next_cursor: "some-cursor",
    });
    renderPage();
    await screen.findByText("dev-1");

    fireEvent.change(
      screen.getByLabelText("Filter loaded rows by batch or device"),
      { target: { value: "no-such-device" } },
    );

    expect(await screen.findByText("No matches in the loaded rows")).toBeInTheDocument();
    expect(
      screen.getByText(/Load more rows, or refine your search/),
    ).toBeInTheDocument();
    expect(screen.queryByText("No batches found")).not.toBeInTheDocument();
  });

  it("shows the summary stat-band once getSummary resolves", async () => {
    mockSummary.mockResolvedValue({
      by_status: { ISSUED: 3, RECEIVED: 7 },
      provisional: 2,
      reasons_histogram: {},
    });
    renderPage();
    await screen.findByText("dev-1");
    expect(await screen.findByText("3")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("getSummary rejecting does not crash the page or redirect", async () => {
    mockSummary.mockRejectedValue(new Error("summary down"));
    renderPage();
    await screen.findByText("dev-1");
    expect(mockNav).not.toHaveBeenCalled();
  });
});
