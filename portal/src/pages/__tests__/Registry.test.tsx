import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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

  it("kiln stepper advances and submits the exact legacy payload shape", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Register new kiln" }));

    // Step 1 — Identity
    fireEvent.change(await screen.findByLabelText("Kiln id"), {
      target: { value: "kiln-9" },
    });
    fireEvent.change(screen.getByLabelText("Type (open/closed)"), {
      target: { value: "open" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    // Step 2 — Build
    fireEvent.change(await screen.findByLabelText("Material"), {
      target: { value: "steel" },
    });
    fireEvent.change(screen.getByLabelText("Weight (kg)"), {
      target: { value: "12" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Next" }));

    // Step 3 — Review shows the values, then submit
    expect(await screen.findByText("kiln-9")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Register kiln" }));

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
