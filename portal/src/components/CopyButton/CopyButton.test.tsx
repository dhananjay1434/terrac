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

  it("announces success via an aria-live region for screen-reader users", () => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn() } });
    render(<CopyButton value="deadbeef" label="Copy hash" />);
    expect(screen.getByRole("status")).toHaveTextContent("");
    fireEvent.click(screen.getByRole("button", { name: "Copy hash" }));
    expect(screen.getByRole("status")).toHaveTextContent("Copied");
  });
});
