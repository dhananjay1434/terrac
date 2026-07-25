import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import BucketToggle from "./BucketToggle";

describe("BucketToggle", () => {
  it("renders both options with correct selected state", () => {
    const onSelect = vi.fn();

    // Test with "month" selected
    const { rerender } = render(
      <BucketToggle selected="month" onSelect={onSelect} />,
    );
    const monthBtn = screen.getByRole("button", { name: "Month" });
    const dayBtn = screen.getByRole("button", { name: "Day" });

    expect(monthBtn).toHaveAttribute("aria-selected", "true");
    expect(monthBtn).toHaveAttribute("aria-pressed", "true");
    expect(dayBtn).toHaveAttribute("aria-selected", "false");
    expect(dayBtn).toHaveAttribute("aria-pressed", "false");

    // Test with "day" selected
    rerender(<BucketToggle selected="day" onSelect={onSelect} />);
    expect(monthBtn).toHaveAttribute("aria-selected", "false");
    expect(monthBtn).toHaveAttribute("aria-pressed", "false");
    expect(dayBtn).toHaveAttribute("aria-selected", "true");
    expect(dayBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSelect when user clicks an option", () => {
    const onSelect = vi.fn();
    render(<BucketToggle selected="month" onSelect={onSelect} />);

    const dayBtn = screen.getByRole("button", { name: "Day" });
    fireEvent.click(dayBtn);

    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("day");
  });

  it("is keyboard accessible with arrow keys toggle between options", () => {
    const onSelect = vi.fn();
    const { rerender } = render(<BucketToggle selected="month" onSelect={onSelect} />);

    const monthBtn = screen.getByRole("button", { name: "Month" });
    const dayBtn = screen.getByRole("button", { name: "Day" });

    // Tab to and focus the month button
    monthBtn.focus();
    expect(monthBtn).toHaveFocus();

    // Press ArrowRight to toggle to day
    fireEvent.keyDown(monthBtn, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenCalledWith("day");
    expect(dayBtn).toHaveFocus();

    // Re-render with selected="day" to simulate state update
    onSelect.mockClear();
    rerender(<BucketToggle selected="day" onSelect={onSelect} />);

    // Now press ArrowLeft to toggle back to month
    fireEvent.keyDown(dayBtn, { key: "ArrowLeft" });
    expect(onSelect).toHaveBeenCalledWith("month");
    expect(monthBtn).toHaveFocus();
  });
});
