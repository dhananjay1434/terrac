import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import VerificationChain from "./VerificationChain";

describe("VerificationChain", () => {
  it("renders every node with its state", () => {
    render(
      <VerificationChain
        nodes={[
          { label: "Received", state: "done" },
          { label: "Evidence", state: "current" },
          { label: "Issued", state: "pending" },
        ]}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(items[0].getAttribute("data-state")).toBe("done");
    expect(screen.getByText("Evidence")).toBeInTheDocument();
  });
});
