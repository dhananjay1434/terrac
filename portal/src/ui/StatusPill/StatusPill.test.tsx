import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import StatusPill, { type PillStatus } from "./StatusPill";

const AXE_OPTS = { runOnly: { type: "tag" as const, values: ["wcag2a", "wcag2aa"] } };

const STATUSES: PillStatus[] = ["success", "warning", "error", "inert"];

describe("StatusPill", () => {
  it.each(STATUSES)("renders the label text for status=%s (never color-only)", (status) => {
    render(<StatusPill status={status}>Issuable</StatusPill>);
    expect(screen.getByText("Issuable")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(<StatusPill status="success">Verified</StatusPill>);
    const results = await axe(container, AXE_OPTS);
    expect(results.violations).toEqual([]);
  });
});
