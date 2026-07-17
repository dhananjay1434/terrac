import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import LabEntry from "../LabEntry";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, submitLabResults: vi.fn(), uploadLabCertificate: vi.fn() };
});

async function sha256Hex(bytes: Uint8Array): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

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
  it("displays the locally computed SHA-256 for a selected certificate", async () => {
    renderPage();
    const bytes = new Uint8Array([1, 2, 3, 4, 5]);
    const expected = await sha256Hex(bytes);
    const file = new File([bytes], "cert.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("Certificate PDF (optional)"), {
      target: { files: [file] },
    });
    const el = await screen.findByTestId("cert-hash");
    await vi.waitFor(() => expect(el.textContent).toBe(expected));
  });

  it("shows the static lab rules preview", () => {
    renderPage();
    expect(
      screen.getByText("Rules that will be checked when you submit"),
    ).toBeInTheDocument();
    expect(screen.getByText("Lab results")).toBeInTheDocument();
  });
});
