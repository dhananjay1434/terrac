import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LabEntry from "../LabEntry";
import { vi } from "vitest";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, submitLabResults: vi.fn(), uploadLabCertificate: vi.fn() };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/lab/abc-uuid"]}>
      <Routes>
        <Route path="/lab/:uuid" element={<LabEntry />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("LabEntry page", () => {
  it("shows a plain attached-file confirmation for a selected certificate", () => {
    renderPage();
    const file = new File([new Uint8Array([1, 2, 3])], "cert.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(screen.getByLabelText("Certificate PDF (optional)"), {
      target: { files: [file] },
    });
    const el = screen.getByTestId("cert-attached");
    expect(el.textContent).toContain("cert.pdf");
    expect(el.textContent).toContain("attached");
  });

  it("shows the honestly-labeled static lab rules preview", () => {
    renderPage();
    expect(screen.getByText("Rules checked on submit")).toBeInTheDocument();
    expect(screen.getByText("Lab results")).toBeInTheDocument();
  });
});
