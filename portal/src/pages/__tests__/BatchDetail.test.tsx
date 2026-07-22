import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import BatchDetail from "../BatchDetail";
import { getBatch, issueCredit, type BatchDetail as Detail } from "../../api";
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
    expect(await screen.findByText("1.234")).toBeInTheDocument();
    expect(screen.getByText("tCO₂e")).toBeInTheDocument();
  });

  it("shows ISSUABLE verdict when compliance.issuable, rendered large in the hero", async () => {
    renderPage();
    const verdict = await screen.findByText("ISSUABLE");
    expect(verdict.closest('[data-size="lg"]')).not.toBeNull();
  });

  it("shows key facts (wet yield, project, received) in the hero figure panel", async () => {
    renderPage();
    await screen.findByText("ISSUABLE");
    // These values also appear elsewhere on the page (Production tile,
    // ProvenanceTile, VerificationChain's "Received" sublabel) — the hero
    // figure panel adds another rendering, so assert at least one exists.
    expect(screen.getAllByText("100 kg").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("p1").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("2026-07-01").length).toBeGreaterThanOrEqual(1);
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

  it("renders the grouped checklist and evidence gallery from one fixture", async () => {
    const d = detail();
    d.media = [
      {
        operation_id: "op1",
        filename: null,
        sha256_hash: "f00dfeedface1234",
        uploaded_at: "2026-07-01T10:00:00Z",
        capture_type: "flame_curtain",
        capture_type_verified: true,
        exif_lat: null,
        exif_lon: null,
        verification_status: null,
        verification_remarks: null,
      },
    ];
    mockGet.mockResolvedValue(d);
    renderPage();
    expect(await screen.findByTestId("group-field")).toBeInTheDocument();
    expect(screen.getByText("Flame curtain photos")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 3, name: /1\. Burn — flame curtain/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("f00dfeedface…")).toBeInTheDocument();
  });

  it("issue modal requires the dynamic token, calls issueCredit, then refetches", async () => {
    const { waitFor } = await import("@testing-library/react");
    mockRole.mockReturnValue("admin");
    const mockIssue = vi.mocked(issueCredit);
    mockIssue.mockResolvedValue({ status: "ISSUED", net_credit_t_co2e: 1.234 });
    renderPage();
    fireEvent.click(await screen.findByRole("button", { name: "Issue credit" }));

    // Dynamic token includes the partial batch uuid.
    expect(screen.getByText(`ISSUE-${UUID.slice(0, 6)}`)).toBeInTheDocument();
    const confirmBtn = screen.getByRole("button", { name: "Issue permanently" });
    expect(confirmBtn).toBeDisabled();

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: `ISSUE-${UUID.slice(0, 6)}` },
    });
    expect(confirmBtn).toBeEnabled();
    const callsBefore = mockGet.mock.calls.length;
    fireEvent.click(confirmBtn);
    await waitFor(() => {
      expect(mockIssue).toHaveBeenCalledWith(UUID);
      expect(mockGet.mock.calls.length).toBeGreaterThan(callsBefore);
    });
  });

  it("does not mount the permanently-empty activity timeline", async () => {
    renderPage();
    await screen.findByText("ISSUABLE");
    expect(screen.queryByTestId("activity-empty")).not.toBeInTheDocument();
  });
});
