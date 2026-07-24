import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import Card from "./Card";

const AXE_OPTS = { runOnly: { type: "tag" as const, values: ["wcag2a", "wcag2aa"] } };

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Body content</Card>);
    expect(screen.getByText("Body content")).toBeInTheDocument();
  });

  it("forwards a custom className alongside its own", () => {
    render(<Card className="extra">x</Card>);
    const el = screen.getByText("x");
    expect(el.className).toContain("extra");
  });

  it("renders as the given tag", () => {
    render(<Card as="section">Sectioned</Card>);
    const el = screen.getByText("Sectioned");
    expect(el.tagName).toBe("SECTION");
  });

  it("has no axe violations", async () => {
    const { container } = render(<Card>Accessible card</Card>);
    const results = await axe(container, AXE_OPTS);
    expect(results.violations).toEqual([]);
  });
});
