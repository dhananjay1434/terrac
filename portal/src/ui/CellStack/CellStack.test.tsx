import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CellStack from "./CellStack";

describe("CellStack", () => {
  it("renders the primary line", () => {
    render(<CellStack primary="Batch #42" />);
    expect(screen.getByText("Batch #42")).toBeInTheDocument();
  });

  it("renders the secondary line when given", () => {
    render(<CellStack primary="Batch #42" secondary="Nairobi, KE" />);
    expect(screen.getByText("Nairobi, KE")).toBeInTheDocument();
  });

  it("omits the secondary node when absent or empty", () => {
    const { container, rerender } = render(<CellStack primary="Batch #42" />);
    expect(container.querySelectorAll("span").length).toBe(2); // wrapper + primary
    rerender(<CellStack primary="Batch #42" secondary="" />);
    expect(container.querySelectorAll("span").length).toBe(2);
  });
});
