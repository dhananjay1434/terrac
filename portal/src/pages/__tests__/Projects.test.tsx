import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Projects from "../Projects";
import {
  createProject,
  listProjects,
  createParcel,
  listParcels,
  listRegistryConfigs,
  ApiError,
  type ProjectRow,
  type SourceParcel,
} from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    createProject: vi.fn(),
    listProjects: vi.fn(),
    createParcel: vi.fn(),
    listParcels: vi.fn(),
    listRegistryConfigs: vi.fn(),
  };
});

const mockCreate = vi.mocked(createProject);
const mockList = vi.mocked(listProjects);
const mockCreateParcel = vi.mocked(createParcel);
const mockListParcels = vi.mocked(listParcels);
const mockListRegistryConfigs = vi.mocked(listRegistryConfigs);

const ROW: ProjectRow = {
  project_id: "proj-1",
  name: "Project One",
  registry_config_id: null,
  org_id: null,
  allowed_feedstocks: ["Lantana_camara"],
  client_target: 25,
  status: "active",
  created_at: "2026-07-01T10:00:00Z",
};

const PARCEL_ROW: SourceParcel = {
  parcel_uuid: "parcel-uuid-1234-5678",
  project_id: "proj-1",
  name: "Parcel Alpha",
  boundary_geojson: '{"type": "Polygon", "coordinates": []}',
  area_m2: 5000,
  declared_area_acres: 1.2,
  bbox_min_lat: 28.6,
  bbox_min_lon: 77.2,
  bbox_max_lat: 28.61,
  bbox_max_lon: 77.21,
  boundary_method: "drawn_polygon",
  boundary_status: "APPROVED",
  created_at: "2026-07-01T10:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/projects"]}>
      <Projects />
    </MemoryRouter>,
  );
}

describe("Projects page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue({ projects: [], next_cursor: null });
    mockListParcels.mockResolvedValue({ parcels: [], next_cursor: null });
    mockListRegistryConfigs.mockResolvedValue({
      registry_configs: [
        {
          config_id: "cfg-1",
          registry_name: "Test Registry",
          methodology_version: "v1",
          params: {
            corg_table: {
              Lantana_camara: 0.6,
              Wood_chips: 0.55,
              Default: 0.55,
            },
          },
          fpic_template_set_id: null,
          created_at: "2026-07-01T10:00:00Z",
        },
      ],
    });
  });

  it("lists existing projects", async () => {
    mockList.mockResolvedValue({ projects: [ROW], next_cursor: null });
    renderPage();
    await screen.findByText("proj-1");
    expect(screen.getByText("Project One")).toBeInTheDocument();
  });

  it("shows the project's feedstock and client target in the table", async () => {
    mockList.mockResolvedValue({ projects: [ROW], next_cursor: null });
    renderPage();
    const row = (await screen.findByText("proj-1")).closest("tr");
    expect(row).not.toBeNull();
    expect(row).toHaveTextContent("Lantana_camara");
    expect(row).toHaveTextContent("25");
  });

  it("populates the feedstock dropdown from registry configs (never hardcoded)", async () => {
    renderPage();
    await screen.findByText("No projects yet");
    const select = screen.getByLabelText("Feedstock") as HTMLSelectElement;
    await waitFor(() => {
      expect(
        Array.from(select.options).map((o) => o.value),
      ).toEqual(expect.arrayContaining(["Lantana_camara", "Wood_chips"]));
    });
    // "Default" is a fallback marker, never a selectable species.
    expect(
      Array.from(select.options).some((o) => o.value === "Default"),
    ).toBe(false);
  });

  it("disables the feedstock dropdown when no registry configs exist", async () => {
    mockListRegistryConfigs.mockResolvedValue({ registry_configs: [] });
    renderPage();
    await screen.findByText("No projects yet");
    const select = await screen.findByLabelText("Feedstock");
    expect(select).toBeDisabled();
  });

  it("shows the empty state when there are no projects", async () => {
    renderPage();
    await screen.findByText("No projects yet");
  });

  it("creates a project and refreshes the list", async () => {
    mockCreate.mockResolvedValue(ROW);
    renderPage();
    await screen.findByText("No projects yet");

    fireEvent.change(screen.getByLabelText("Project ID"), {
      target: { value: "proj-1" },
    });
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Project One" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        project_id: "proj-1",
        name: "Project One",
        allowed_feedstocks: [],
        client_target: undefined,
      });
    });
    await screen.findByText("✓ Project created");
  });

  it("submits the selected feedstock and client target", async () => {
    mockCreate.mockResolvedValue(ROW);
    renderPage();
    await screen.findByText("No projects yet");

    fireEvent.change(screen.getByLabelText("Project ID"), {
      target: { value: "proj-1" },
    });
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Project One" },
    });
    const select = await screen.findByLabelText("Feedstock");
    await waitFor(() => expect(select).not.toBeDisabled());
    fireEvent.change(select, { target: { value: "Wood_chips" } });
    fireEvent.change(screen.getByLabelText("Client Target"), {
      target: { value: "25" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith({
        project_id: "proj-1",
        name: "Project One",
        allowed_feedstocks: ["Wood_chips"],
        client_target: 25,
      });
    });
  });

  it("surfaces a clear message when the feedstock is not on the positive list (422)", async () => {
    mockCreate.mockRejectedValue(
      new ApiError(
        422,
        JSON.stringify({
          error: "feedstock_not_in_positive_list",
          unknown: ["Bogus_species"],
          allowed: ["Lantana_camara", "Wood_chips"],
        }),
      ),
    );
    renderPage();
    await screen.findByText("No projects yet");

    fireEvent.change(screen.getByLabelText("Project ID"), {
      target: { value: "proj-bad" },
    });
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Bad" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    await screen.findByText(/Not on the positive list: Bogus_species/);
  });

  it("registers a source parcel boundary", async () => {
    mockList.mockResolvedValue({ projects: [ROW], next_cursor: null });
    mockCreateParcel.mockResolvedValue(PARCEL_ROW);
    renderPage();

    await screen.findByText("proj-1");

    fireEvent.change(screen.getByLabelText("Parcel Name"), {
      target: { value: "Parcel Alpha" },
    });

    const polygon = {
      type: "Polygon",
      coordinates: [
        [
          [77.2, 28.6],
          [77.21, 28.6],
          [77.21, 28.61],
          [77.2, 28.61],
          [77.2, 28.6],
        ],
      ],
    };

    fireEvent.change(screen.getByLabelText(/Boundary GeoJSON/i), {
      target: { value: JSON.stringify(polygon) },
    });

    const submitBtn = await screen.findByRole("button", { name: "Register Boundary" });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockCreateParcel).toHaveBeenCalledWith({
        project_id: "proj-1",
        name: "Parcel Alpha",
        boundary_geojson: expect.objectContaining({ type: "Polygon" }),
        declared_area_acres: undefined,
      });
    });
    await screen.findByText("✓ Source parcel boundary registered & approved");
  });

  it("rejects an empty submission client-side without calling the API", async () => {
    renderPage();
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
    await screen.findByText("Project ID and name are required");
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("surfaces a clear message on a duplicate project_id (409)", async () => {
    mockCreate.mockRejectedValue(new ApiError(409, "project_already_exists"));
    renderPage();

    fireEvent.change(screen.getByLabelText("Project ID"), {
      target: { value: "proj-dup" },
    });
    fireEvent.change(screen.getByLabelText("Project name"), {
      target: { value: "Dup" },
    });
    fireEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    await screen.findByText("A project with that ID already exists");
  });
});
