import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import BucketToggle from "./BucketToggle";

const OPTS = [
  { value: "month", label: "Month" },
  { value: "week", label: "Week" },
  { value: "day", label: "Day" },
];

describe("BucketToggle", () => {
  it("renders all options with correct selected state", () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <BucketToggle options={OPTS} selected="month" onSelect={onSelect} />,
    );
    const monthBtn = screen.getByRole("button", { name: "Month" });
    const weekBtn = screen.getByRole("button", { name: "Week" });
    const dayBtn = screen.getByRole("button", { name: "Day" });

    expect(monthBtn).toHaveAttribute("aria-selected", "true");
    expect(monthBtn).toHaveAttribute("aria-pressed", "true");
    expect(weekBtn).toHaveAttribute("aria-selected", "false");
    expect(dayBtn).toHaveAttribute("aria-selected", "false");

    rerender(<BucketToggle options={OPTS} selected="day" onSelect={onSelect} />);
    expect(monthBtn).toHaveAttribute("aria-selected", "false");
    expect(dayBtn).toHaveAttribute("aria-selected", "true");
    expect(dayBtn).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onSelect with the clicked option's value", () => {
    const onSelect = vi.fn();
    render(<BucketToggle options={OPTS} selected="month" onSelect={onSelect} />);

    fireEvent.click(screen.getByRole("button", { name: "Week" }));
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("week");
  });

  it("navigates with arrow keys (roving focus, wraps around)", () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <BucketToggle options={OPTS} selected="month" onSelect={onSelect} />,
    );
    const monthBtn = screen.getByRole("button", { name: "Month" });
    const weekBtn = screen.getByRole("button", { name: "Week" });
    const dayBtn = screen.getByRole("button", { name: "Day" });

    monthBtn.focus();
    // ArrowRight month -> week
    fireEvent.keyDown(monthBtn, { key: "ArrowRight" });
    expect(onSelect).toHaveBeenCalledWith("week");
    expect(weekBtn).toHaveFocus();

    // ArrowLeft from the first option wraps to the last (day)
    onSelect.mockClear();
    rerender(<BucketToggle options={OPTS} selected="month" onSelect={onSelect} />);
    monthBtn.focus();
    fireEvent.keyDown(monthBtn, { key: "ArrowLeft" });
    expect(onSelect).toHaveBeenCalledWith("day");
    expect(dayBtn).toHaveFocus();
  });
});
