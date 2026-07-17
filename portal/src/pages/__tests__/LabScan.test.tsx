import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import LabScan from "../LabScan";

const mockNav = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNav };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/lab/scan"]}>
      <LabScan />
    </MemoryRouter>,
  );
}

describe("LabScan page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("renders recent scans from localStorage", () => {
    localStorage.setItem(
      "tc_recent_scans",
      JSON.stringify(["aaaa1111-2222-3333-4444-555566667777"]),
    );
    renderPage();
    expect(
      screen.getByRole("button", {
        name: "Open batch aaaa1111-2222-3333-4444-555566667777",
      }),
    ).toBeInTheDocument();
  });

  it("manual entry navigates and records the scan", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Batch UUID"), {
      target: { value: "  bbbb-uuid  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(mockNav).toHaveBeenCalledWith("/lab/bbbb-uuid");
    expect(
      JSON.parse(localStorage.getItem("tc_recent_scans") ?? "[]"),
    ).toContain("bbbb-uuid");
  });
});
