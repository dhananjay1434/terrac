import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DetailDrawer from "./DetailDrawer";

describe("DetailDrawer", () => {
  it("renders the title and body content when open", () => {
    render(
      <DetailDrawer open onOpenChange={vi.fn()} title="Dispatch detail">
        <div>panel body</div>
      </DetailDrawer>,
    );
    expect(screen.getByText("Dispatch detail")).toBeInTheDocument();
    expect(screen.getByText("panel body")).toBeInTheDocument();
  });

  it("renders nothing when closed", () => {
    render(
      <DetailDrawer open={false} onOpenChange={vi.fn()} title="Dispatch detail">
        <div>panel body</div>
      </DetailDrawer>,
    );
    expect(screen.queryByText("panel body")).not.toBeInTheDocument();
  });

  it("calls onOpenChange(false) when the close button is clicked", () => {
    const onOpenChange = vi.fn();
    render(
      <DetailDrawer open onOpenChange={onOpenChange} title="Dispatch detail">
        <div>panel body</div>
      </DetailDrawer>,
    );
    fireEvent.click(screen.getByRole("button", { name: "Close" }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("calls onOpenChange(false) on Escape", () => {
    const onOpenChange = vi.fn();
    render(
      <DetailDrawer open onOpenChange={onOpenChange} title="Dispatch detail">
        <div>panel body</div>
      </DetailDrawer>,
    );
    fireEvent.keyDown(screen.getByText("panel body"), { key: "Escape" });
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });
});
