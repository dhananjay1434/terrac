import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import * as Tooltip from "@radix-ui/react-tooltip";
import LabEntry from "../LabEntry";
import { vi } from "vitest";

vi.mock("../../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api")>();
  return { ...actual, submitLabResults: vi.fn(), uploadLabCertificate: vi.fn() };
});

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/lab/abc-uuid"]}>
      <Tooltip.Provider>
        <Routes>
          <Route path="/lab/:uuid" element={<LabEntry />} />
        </Routes>
      </Tooltip.Provider>
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

  it("renders the Submit results button and keeps the attached-file confirmation after reskinning", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: "Submit results" }),
    ).toBeInTheDocument();

    const file = new File([new Uint8Array([1, 2, 3])], "cert2.pdf", {
      type: "application/pdf",
    });
    fireEvent.change(screen.getByLabelText("Certificate PDF (optional)"), {
      target: { files: [file] },
    });
    const el = screen.getByTestId("cert-attached");
    expect(el.textContent).toContain("cert2.pdf");
    expect(el.textContent).toContain("attached");
  });

  it("renders a validation message under the specific field it belongs to", () => {
    renderPage();
    const moisture = screen.getByLabelText(
      "Biochar moisture samples (≥3, comma sep.)",
    );
    // One sample fails the ≥3 rule.
    fireEvent.change(moisture, { target: { value: "5" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit results" }));

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent(
      "Provide at least 3 biochar moisture samples.",
    );
    // The failing input is wired to its message for assistive tech.
    expect(moisture).toHaveAttribute("aria-invalid", "true");
    expect(moisture).toHaveAttribute("aria-describedby", alert.id);
  });
});
