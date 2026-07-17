import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Registry from "../Registry";
import { registryPost, listKilns } from "../../api";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return {
    ...actual,
    registryPost: vi.fn().mockResolvedValue({}),
    listKilns: vi.fn().mockResolvedValue({ kilns: [] }),
    mintToken: vi.fn(),
  };
});

const mockPost = vi.mocked(registryPost);
const mockKilns = vi.mocked(listKilns);

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/registry"]}>
      <Registry />
    </MemoryRouter>,
  );
}

describe("Registry page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPost.mockResolvedValue({});
    mockKilns.mockResolvedValue({ kilns: [] });
  });

  it("registers a kiln via a single inline form and submits the exact legacy payload shape", async () => {
    renderPage();

    const kilnForm = screen
      .getByText("Register kiln (C8)")
      .closest("form")!;
    fireEvent.change(
      within(kilnForm).getByLabelText("kiln id"),
      { target: { value: "kiln-9" } },
    );
    fireEvent.change(
      within(kilnForm).getByLabelText("type (open/closed)"),
      { target: { value: "open" } },
    );
    fireEvent.change(within(kilnForm).getByLabelText("material"), {
      target: { value: "steel" },
    });
    fireEvent.change(within(kilnForm).getByLabelText("weight kg"), {
      target: { value: "12" },
    });
    fireEvent.click(within(kilnForm).getByRole("button", { name: "Save" }));

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith("kilns", {
        kiln_id: "kiln-9",
        kiln_type: "open",
        material: "steel",
        weight_kg: 12,
      });
    });
  });

  it("renders the three registry tabs", () => {
    renderPage();
    expect(screen.getByRole("tab", { name: "Kilns" })).toBeInTheDocument();
    expect(
      screen.getByRole("tab", { name: "Operator training" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Standards" })).toBeInTheDocument();
  });
});
