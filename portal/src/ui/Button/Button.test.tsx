import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe } from "jest-axe";
import Button from "./Button";

const AXE_OPTS = { runOnly: { type: "tag" as const, values: ["wcag2a", "wcag2aa"] } };

describe("Button", () => {
  it("renders each variant with its label", () => {
    const { rerender } = render(<Button variant="primary">Save</Button>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    rerender(<Button variant="neutral">Cancel</Button>);
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
    rerender(<Button variant="ghost">Dismiss</Button>);
    expect(screen.getByRole("button", { name: "Dismiss" })).toBeInTheDocument();
  });

  it("fires onClick when clicked", () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    fireEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("loading disables the button and sets aria-busy, and blocks clicks", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Submitting
      </Button>,
    );
    const btn = screen.getByRole("button", { name: "Submitting" });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute("aria-busy", "true");
    fireEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is keyboard-focusable and has no axe violations", async () => {
    const { container } = render(<Button>Focus me</Button>);
    const btn = screen.getByRole("button", { name: "Focus me" });
    btn.focus();
    expect(btn).toHaveFocus();
    const results = await axe(container, AXE_OPTS);
    expect(results.violations).toEqual([]);
  });
});
