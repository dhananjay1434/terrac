import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import SealedVerdict from "./SealedVerdict";

describe("SealedVerdict", () => {
  it("renders ISSUABLE without a count", () => {
    render(<SealedVerdict verdict="ISSUABLE" reasonCount={0} />);
    expect(screen.getByText("ISSUABLE")).toBeInTheDocument();
    expect(screen.queryByText(/blocker/)).not.toBeInTheDocument();
  });

  it("renders PROVISIONAL with the blocker count", () => {
    render(<SealedVerdict verdict="PROVISIONAL" reasonCount={2} />);
    expect(screen.getByText("PROVISIONAL")).toBeInTheDocument();
    expect(screen.getByText("2 blockers")).toBeInTheDocument();
  });

  it("defaults to size md, and can be rendered lg", () => {
    const { rerender, getByText } = render(
      <SealedVerdict verdict="ISSUABLE" />,
    );
    expect(getByText("ISSUABLE").getAttribute("data-size")).toBe("md");
    rerender(<SealedVerdict verdict="ISSUABLE" size="lg" />);
    expect(getByText("ISSUABLE").getAttribute("data-size")).toBe("lg");
  });
});
