import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CopyButton from "./CopyButton";

describe("CopyButton", () => {
  it("copies the value to the clipboard", () => {
    const writeText = vi.fn();
    Object.assign(navigator, { clipboard: { writeText } });
    render(<CopyButton value="deadbeef" label="Copy hash" />);
    fireEvent.click(screen.getByRole("button", { name: "Copy hash" }));
    expect(writeText).toHaveBeenCalledWith("deadbeef");
  });
});
