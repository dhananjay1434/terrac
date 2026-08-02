import { describe, it, expect } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TelemetryCard from "./TelemetryCard";

function Card() {
  return (
    <TelemetryCard title="Real-time thermal mapping" expandedChildren={<div>big chart</div>}>
      <div>small chart</div>
    </TelemetryCard>
  );
}

describe("TelemetryCard", () => {
  it("shows the compact chart inline, not the expanded one", () => {
    render(<Card />);
    expect(screen.getByText("small chart")).toBeInTheDocument();
    expect(screen.queryByText("big chart")).toBeNull();
  });

  it("clicking the card opens the expand modal with the large chart", async () => {
    render(<Card />);
    fireEvent.click(screen.getByRole("button", { name: /expand real-time thermal mapping/i }));
    await waitFor(() => expect(screen.getByText("big chart")).toBeInTheDocument());
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("Enter/Space on the card opens the modal (keyboard-activatable)", async () => {
    render(<Card />);
    const card = screen.getByRole("button", { name: /expand real-time thermal mapping/i });
    fireEvent.keyDown(card, { key: "Enter" });
    await waitFor(() => expect(screen.getByText("big chart")).toBeInTheDocument());
  });

  it("Close button dismisses the modal", async () => {
    render(<Card />);
    fireEvent.click(screen.getByRole("button", { name: /expand real-time thermal mapping/i }));
    await waitFor(() => expect(screen.getByText("big chart")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /close/i }));
    await waitFor(() => expect(screen.queryByText("big chart")).toBeNull());
  });
});
