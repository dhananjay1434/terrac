import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Farmers from "../Farmers";
import {
  listFarmers,
  getFarmer,
  type FarmerRow,
  type FarmerDetail,
} from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, listFarmers: vi.fn(), getFarmer: vi.fn() };
});

const mockList = vi.mocked(listFarmers);
const mockGet = vi.mocked(getFarmer);

const ROW: FarmerRow = {
  farmer_uuid: "f-1",
  project_id: "proj-1",
  first_name: "Asha",
  last_name: "Devi",
  mobile_number: "9990001111",
  village: "Rampur",
  kyc_status: "verified",
  consent_status: "signed",
  created_at: "2026-07-01T10:00:00Z",
};

const DETAIL: FarmerDetail = {
  ...ROW,
  gender: "F",
  guardian_name: "Ram Devi",
  dob: "1990-01-01T00:00:00Z",
  education: null,
  family_size: 4,
  reported_area: 1.5,
  signature_media_id: null,
  sync_status: "synced",
  documents: [{ id: 1, doc_type: "aadhaar", last4: "1234", media_id: "m1" }],
  payments: [
    {
      id: 1,
      rail: "bank",
      account_holder: "Asha Devi",
      masked_account: "XXXXXX3210",
      ifsc_code: "HDFC0001234",
      masked_upi_id: null,
      masked_mfs_id: null,
    },
  ],
  consents: [
    {
      id: 1,
      fpic_template_id: "fpic-v1",
      signed_pdf_media_id: "pdf1",
      holding_photo_media_id: "ph1",
      signed_at: "2026-07-01T10:00:00Z",
      exclusivity_ack: true,
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/farmers"]}>
      <Farmers />
    </MemoryRouter>,
  );
}

describe("Farmers page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ items: [], total: 0, page: 1, size: 25 });
  });

  it("lists farmers", async () => {
    mockList.mockResolvedValue({ items: [ROW], total: 1, page: 1, size: 25 });
    renderPage();
    await screen.findByText("Asha Devi");
    expect(screen.getByText("Rampur")).toBeInTheDocument();
  });

  it("shows the empty state when there are none", async () => {
    renderPage();
    await screen.findByText("No farmers found");
  });

  it("searches by name/mobile", async () => {
    mockList.mockResolvedValue({ items: [ROW], total: 1, page: 1, size: 25 });
    renderPage();
    await screen.findByText("Asha Devi");

    fireEvent.change(screen.getByLabelText(/Search farmers/i), {
      target: { value: "9990" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() => {
      expect(mockList).toHaveBeenLastCalledWith(
        expect.objectContaining({ search: "9990", page: 1 }),
      );
    });
  });

  it("opens a detail panel showing masked PII only", async () => {
    mockList.mockResolvedValue({ items: [ROW], total: 1, page: 1, size: 25 });
    mockGet.mockResolvedValue(DETAIL);
    renderPage();

    fireEvent.click(await screen.findByText("Asha Devi"));

    // last-4 document + masked account are shown; no full numbers.
    await screen.findByText(/••••1234/);
    expect(screen.getByText(/XXXXXX3210/)).toBeInTheDocument();
    expect(mockGet).toHaveBeenCalledWith("f-1");
  });
});
