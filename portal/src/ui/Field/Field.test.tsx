import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import Field from "./Field";

describe("Field (audit P5.1)", () => {
  it("renders label, required mark and hint", () => {
    render(
      <Field label="Kiln ID" htmlFor="kiln" required hint="From the kiln card">
        <input id="kiln" />
      </Field>,
    );
    expect(screen.getByText("Kiln ID")).toBeInTheDocument();
    expect(screen.getByText("*")).toBeInTheDocument();
    expect(screen.getByText("From the kiln card")).toBeInTheDocument();
  });

  it("error replaces hint, is an alert, and wires the control", () => {
    render(
      <Field label="H:Corg" htmlFor="hc" hint="0.1–1.5" error="Out of range">
        <input id="hc" />
      </Field>,
    );
    // Hint is hidden while an error is present.
    expect(screen.queryByText("0.1–1.5")).not.toBeInTheDocument();
    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("Out of range");
    const input = screen.getByRole("textbox");
    expect(input).toHaveAttribute("aria-invalid", "true");
    expect(input.getAttribute("aria-describedby")).toBe(alert.id);
  });
});
