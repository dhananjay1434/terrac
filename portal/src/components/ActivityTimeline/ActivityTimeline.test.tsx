import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ActivityTimeline from "./ActivityTimeline";

describe("ActivityTimeline", () => {
  it("renders events in the given (chronological) order", () => {
    render(
      <ActivityTimeline
        events={[
          { id: "1", actor: "field device", action: "synced batch", at: "2026-07-01T09:00:00Z" },
          { id: "2", actor: "admin", action: "issued credit", at: "2026-07-02T10:00:00Z" },
        ]}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0].textContent).toContain("field device");
    expect(items[1].textContent).toContain("issued credit");
  });

  it("renders the empty state when there are no events", () => {
    render(<ActivityTimeline events={[]} />);
    expect(screen.getByTestId("activity-empty")).toBeInTheDocument();
    expect(
      screen.getByText("Activity log will appear here once the backend exposes it."),
    ).toBeInTheDocument();
  });
});
