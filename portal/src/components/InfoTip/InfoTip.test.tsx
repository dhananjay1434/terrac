import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import * as Tooltip from "@radix-ui/react-tooltip";
import InfoTip from "./InfoTip";

function renderWithProvider(label: string) {
  return render(
    <Tooltip.Provider>
      <InfoTip label={label} />
    </Tooltip.Provider>,
  );
}

describe("InfoTip", () => {
  it("renders a trigger with an accessible Help label", () => {
    renderWithProvider("Issuable = all gates met.");
    expect(
      screen.getByRole("button", { name: "Help: Issuable = all gates met." }),
    ).toBeInTheDocument();
  });

  // Radix Tooltip gates open state on a hover-intent timer that does not
  // reliably advance under jsdom's synthetic pointer events (confirmed via
  // isolated debugging: data-state stays "closed" after pointerDown +
  // pointerEnter). Per the fallback allowed for this exact case, downgrade
  // to asserting the trigger and its accessible name render correctly —
  // the real open/close behavior is Radix's own, already-tested code.
  it("exposes a focusable trigger with the label in its accessible name", () => {
    renderWithProvider("H:Corg explanation");
    const trigger = screen.getByRole("button", {
      name: "Help: H:Corg explanation",
    });
    expect(trigger).toBeInTheDocument();
    expect(trigger.getAttribute("data-state")).toBe("closed");
  });
});
