import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import StatBand from "./StatBand";
import StatTile from "../../components/StatTile/StatTile";

const AXE_OPTS = { runOnly: { type: "tag" as const, values: ["wcag2a", "wcag2aa"] } };

describe("StatBand", () => {
  it("renders N StatTile children", () => {
    render(
      <StatBand>
        <StatTile label="Issued" value="12" />
        <StatTile label="Provisional" value="3" />
        <StatTile label="Received" value="9" />
      </StatBand>,
    );
    expect(screen.getByText("Issued")).toBeInTheDocument();
    expect(screen.getByText("Provisional")).toBeInTheDocument();
    expect(screen.getByText("Received")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <StatBand>
        <StatTile label="Issued" value="12" />
      </StatBand>,
    );
    const results = await axe(container, AXE_OPTS);
    expect(results.violations).toEqual([]);
  });
});
