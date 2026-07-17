import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import StatTile from "./StatTile";

describe("StatTile", () => {
  it("renders label and value", () => {
    render(<StatTile label="Issued" value="3" />);
    expect(screen.getByText("Issued")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("renders an optional hint", () => {
    render(<StatTile label="Credit" value="1.234" hint="loaded rows" />);
    expect(screen.getByText("loaded rows")).toBeInTheDocument();
  });
});
