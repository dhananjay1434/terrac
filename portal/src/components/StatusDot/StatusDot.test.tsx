import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatusDot from "./StatusDot";

describe("StatusDot", () => {
  it("renders the label and exposes the variant", () => {
    const { container } = render(<StatusDot variant="warning" label="Provisional" />);
    expect(screen.getByText("Provisional")).toBeInTheDocument();
    expect(container.querySelector('[data-variant="warning"]')).not.toBeNull();
  });

  it("renders without a label", () => {
    const { container } = render(<StatusDot variant="success" />);
    expect(container.querySelector('[data-variant="success"]')).not.toBeNull();
  });
});
