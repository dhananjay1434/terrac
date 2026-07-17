import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MetricBlock from "./MetricBlock";

describe("MetricBlock", () => {
  it("renders value, unit and caption", () => {
    render(<MetricBlock value="1.23" unit="tCO₂e" caption="net credit" />);
    expect(screen.getByText("1.23")).toBeInTheDocument();
    expect(screen.getByText("tCO₂e")).toBeInTheDocument();
    expect(screen.getByText("net credit")).toBeInTheDocument();
  });
});
