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

  it("manual entry navigates and records the scan for a valid uuid", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Batch UUID"), {
      target: { value: "  BBBB1111-2222-3333-4444-555566667777  " },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(mockNav).toHaveBeenCalledWith(
      "/lab/bbbb1111-2222-3333-4444-555566667777",
    );
    expect(
      JSON.parse(localStorage.getItem("tc_recent_scans") ?? "[]"),
    ).toContain("bbbb1111-2222-3333-4444-555566667777");
  });

  it("also accepts the dmrv-batch:v1: QR payload form typed manually", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Batch UUID"), {
      target: {
        value: "dmrv-batch:v1:cccc1111-2222-3333-4444-555566667777",
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(mockNav).toHaveBeenCalledWith(
      "/lab/cccc1111-2222-3333-4444-555566667777",
    );
  });

  it("rejects garbage input — no navigation, no recent-scan write, shows an error", () => {
    renderPage();
    fireEvent.change(screen.getByLabelText("Batch UUID"), {
      target: { value: "not-a-real-code" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Open" }));
    expect(mockNav).not.toHaveBeenCalled();
    expect(
      JSON.parse(localStorage.getItem("tc_recent_scans") ?? "[]"),
    ).toEqual([]);
    expect(screen.getByText("Not a valid batch code.")).toBeInTheDocument();
  });
});
