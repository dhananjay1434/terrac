import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ProvenanceTile from "./ProvenanceTile";

describe("ProvenanceTile", () => {
  it("renders available fields and em-dash for missing ones", () => {
    render(
      <ProvenanceTile
        batchUuid="aaaa1111-2222-3333-4444-555566667777"
        deviceId="dev-1"
        projectId={null}
        receivedAt="2026-07-01T10:00:00Z"
      />,
    );
    expect(screen.getByText("dev-1")).toBeInTheDocument();
    expect(screen.getByText("Methodology")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("2026-07-01 10:00")).toBeInTheDocument();
  });
});
