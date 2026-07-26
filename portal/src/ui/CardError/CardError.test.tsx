import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import CardError from "./CardError";

describe("CardError (audit D5)", () => {
  it("shows the message", () => {
    render(<CardError message="Failed to load batches." />);
    expect(screen.getByText("Failed to load batches.")).toBeInTheDocument();
  });

  it("renders a retry button that fires onRetry", () => {
    const onRetry = vi.fn();
    render(<CardError message="Failed." onRetry={onRetry} />);
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });

  it("omits the retry button when no onRetry is given", () => {
    render(<CardError message="Failed." />);
    expect(screen.queryByRole("button", { name: "Retry" })).not.toBeInTheDocument();
  });
});
