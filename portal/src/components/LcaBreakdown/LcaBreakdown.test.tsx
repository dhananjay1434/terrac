import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import LcaBreakdown from "./LcaBreakdown";

describe("LcaBreakdown", () => {
  it("renders wet yield and net credit from real fields only", () => {
    render(<LcaBreakdown wetYieldKg={100} netCreditTCo2e={1.234} />);
    expect(screen.getByText("100 kg")).toBeInTheDocument();
    expect(screen.getByText("1.234 tCO₂e")).toBeInTheDocument();
  });
});
