import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BatchDetail from "../BatchDetail";
import { getBatch, type BatchDetail as Detail } from "../../api";
import { getRole } from "../../auth";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    getBatch: vi.fn(),
    fetchMediaUrl: vi.fn().mockResolvedValue("blob:mock"),
    issueCredit: vi.fn(),
  };
});
vi.mock("../../auth", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../auth")>();
  return { ...actual, getRole: vi.fn() };
});

const mockGet = vi.mocked(getBatch);
const mockRole = vi.mocked(getRole);

const UUID = "aaaa1111-2222-3333-4444-555566667777";

function detail(over: Partial<Detail["compliance"]> = {}): Detail {
  return {
    batch: {
      batch_uuid: UUID,
      device_id: "dev-1",
      project_id: "p1",
      status: "RECEIVED",
      provisional: false,
      reason_count: 0,
      net_credit_t_co2e: 1.234,
      wet_yield_kg: 100,
      received_at: "2026-07-01T10:00:00Z",
    },
    compliance: {
      batch_uuid: UUID,
      provisional: false,
      issuable: true,
      reasons: [],
      checklist: [
        {
          code: "C1",
          section: "per-run (C1)",
          label: "Flame curtain photos",
          ok: true,
          enforcement: "enforced",
        },
      ],
      ...over,
    },
    evidence_counts: { moisture_readings: 3 },
    media: [],
  };
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/batches/${UUID}`]}>
      <Routes>
        <Route path="/batches/:uuid" element={<BatchDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("BatchDetail page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRole.mockReturnValue("verifier");
    mockGet.mockResolvedValue(detail());
  });

  it("renders the credit MetricBlock with the correct value", async () => {
    renderPage();
    expect(await screen.findByText("1.23")).toBeInTheDocument();
    expect(screen.getByText("tCO₂e")).toBeInTheDocument();
  });

  it("shows ISSUABLE verdict when compliance.issuable", async () => {
    renderPage();
    expect(await screen.findByText("ISSUABLE")).toBeInTheDocument();
  });

  it("shows PROVISIONAL with blocker count when not issuable", async () => {
    mockGet.mockResolvedValue(
      detail({ issuable: false, provisional: true, reasons: ["a", "b"] }),
    );
    renderPage();
    expect(await screen.findByText("PROVISIONAL")).toBeInTheDocument();
    expect(screen.getByText("2 blockers")).toBeInTheDocument();
  });

  it("copy button copies the full batch uuid", async () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    renderPage();
    await screen.findByText("ISSUABLE");
    fireEvent.click(screen.getAllByRole("button", { name: "Copy batch id" })[0]);
    expect(writeText).toHaveBeenCalledWith(UUID);
  });

  it("admin-only actions render only for admins", async () => {
    renderPage();
    await screen.findByText("ISSUABLE");
    expect(
      screen.queryByRole("button", { name: "Issue credit" }),
    ).not.toBeInTheDocument();

    mockRole.mockReturnValue("admin");
    mockGet.mockResolvedValue(detail());
    renderPage();
    expect(
      await screen.findByRole("button", { name: "Issue credit" }),
    ).toBeInTheDocument();
  });

  it("renders the 4-node verification chain", async () => {
    renderPage();
    await screen.findByText("ISSUABLE");
    const chain = screen.getByRole("list", { name: "Verification chain" });
    expect(chain.querySelectorAll("li")).toHaveLength(4);
  });

  it("renders skeletons while getBatch is unresolved", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    const { container } = renderPage();
    expect(container.querySelectorAll(".skeleton").length).toBeGreaterThan(0);
  });
});
