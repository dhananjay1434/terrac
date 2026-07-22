import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";
import Dispatch from "../Dispatch";
import {
  listDispatch,
  listFacilities,
  createFacility,
  ApiError,
  type DispatchRow,
  type FacilityRow,
} from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    listDispatch: vi.fn(),
    listFacilities: vi.fn(),
    createFacility: vi.fn(),
  };
});

const mockListDispatch = vi.mocked(listDispatch);
const mockListFacilities = vi.mocked(listFacilities);
const mockCreateFacility = vi.mocked(createFacility);

const DRAFT_ROW: DispatchRow = {
  dispatch_uuid: "dispatch-uuid-aaaa1111",
  kind: "biomass",
  source_ref: null,
  dest_facility_uuid: null,
  status: "draft",
  weight_source_kg: 100,
  weight_facility_kg: null,
  weight_delta_pct: null,
  weight_flagged: null,
  driver_name: "Ramesh",
  truck_number: "DL01AB1234",
  device_id: "dev-1",
  created_at: "2026-07-22T10:00:00Z",
  received_at: null,
};

const FLAGGED_ROW: DispatchRow = {
  ...DRAFT_ROW,
  dispatch_uuid: "dispatch-uuid-bbbb2222",
  status: "received",
  weight_facility_kg: 70,
  weight_delta_pct: 30.0,
  weight_flagged: true,
  received_at: "2026-07-22T12:00:00Z",
};

const FACILITY_ROW: FacilityRow = {
  facility_uuid: "facility-uuid-1",
  name: "North Facility",
  facility_type: "industrial",
  state: null,
  district: null,
  latitude: null,
  longitude: null,
  status: "active",
  created_at: "2026-07-01T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/dispatch"]}>
      <Tooltip.Provider>
        <Dispatch />
      </Tooltip.Provider>
    </MemoryRouter>,
  );
}

describe("Dispatch page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListDispatch.mockResolvedValue({ dispatches: [], next_cursor: null });
    mockListFacilities.mockResolvedValue({ facilities: [], next_cursor: null });
  });

  it("lists dispatches", async () => {
    mockListDispatch.mockResolvedValue({ dispatches: [DRAFT_ROW], next_cursor: null });
    renderPage();
    await screen.findByText("Ramesh");
    expect(screen.getByText("DL01AB1234")).toBeInTheDocument();
  });

  it("shows the empty state when there are none", async () => {
    renderPage();
    await screen.findByText("No dispatches found");
  });

  it("shows a flagged weight-discrepancy chip", async () => {
    mockListDispatch.mockResolvedValue({ dispatches: [FLAGGED_ROW], next_cursor: null });
    renderPage();
    await screen.findByText(/Flagged \(30\.0%\)/);
  });

  it("filters by status tab", async () => {
    renderPage();
    await waitFor(() => expect(mockListDispatch).toHaveBeenCalled());

    const tab = screen.getByRole("tab", { name: "In-Transit" });
    fireEvent.mouseDown(tab, { button: 0 });
    fireEvent.click(tab);

    await waitFor(() => {
      expect(mockListDispatch).toHaveBeenLastCalledWith(
        expect.objectContaining({ status: "in_transit" }),
      );
    });
  });

  it("registers a facility", async () => {
    mockCreateFacility.mockResolvedValue(FACILITY_ROW);
    renderPage();

    fireEvent.change(screen.getByLabelText("Facility UUID"), {
      target: { value: "facility-uuid-1" },
    });
    fireEvent.change(screen.getByLabelText("Facility name"), {
      target: { value: "North Facility" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(mockCreateFacility).toHaveBeenCalledWith({
        facility_uuid: "facility-uuid-1",
        name: "North Facility",
        facility_type: "artisanal",
      });
    });
    await screen.findByText("✓ Facility registered");
  });

  it("rejects an empty facility submission client-side", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    await screen.findByText("Facility UUID and name are required");
    expect(mockCreateFacility).not.toHaveBeenCalled();
  });

  it("surfaces a duplicate-facility conflict", async () => {
    mockCreateFacility.mockRejectedValue(new ApiError(409, "facility_already_exists"));
    renderPage();

    fireEvent.change(screen.getByLabelText("Facility UUID"), {
      target: { value: "dup-uuid" },
    });
    fireEvent.change(screen.getByLabelText("Facility name"), {
      target: { value: "Dup" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save" }));

    await screen.findByText("A facility with that UUID already exists");
  });
});
