import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { axe } from "jest-axe";
import HorizontalBarList from "./HorizontalBarList";

describe("HorizontalBarList", () => {
  it("sorts descending and renders label + value per row", () => {
    render(
      <HorizontalBarList
        items={[
          { label: "Beta", value: 1 },
          { label: "Alpha", value: 5 },
        ]}
        ariaLabel="test"
      />,
    );
    const rows = screen.getAllByRole("listitem");
    expect(rows[0]).toHaveTextContent("Alpha");
    expect(rows[0]).toHaveTextContent("5");
    expect(rows[1]).toHaveTextContent("Beta");
  });

  it("emphasizes the top bar only when it is a STRICT leader", () => {
    const { container: strict } = render(
      <HorizontalBarList items={[{ label: "A", value: 5 }, { label: "B", value: 2 }]} />,
    );
    expect(strict.querySelector('[data-top="true"]')).not.toBeNull();

    const { container: flat } = render(
      <HorizontalBarList items={[{ label: "A", value: 3 }, { label: "B", value: 3 }]} />,
    );
    // All-equal breakdown: no misleading standout.
    expect(flat.querySelector('[data-top="true"]')).toBeNull();
  });

  it("bar widths are proportional to value (max fills the track)", () => {
    const { container } = render(
      <HorizontalBarList items={[{ label: "A", value: 10 }, { label: "B", value: 5 }]} />,
    );
    const fills = container.querySelectorAll<HTMLElement>('[class*="fill"]');
    expect(fills[0].style.width).toBe("100%");
    expect(fills[1].style.width).toBe("50%");
  });

  it("collapses the long tail past maxItems into one Other row", () => {
    const items = Array.from({ length: 12 }, (_, i) => ({
      label: `R${i}`,
      value: 12 - i,
    }));
    render(<HorizontalBarList items={items} maxItems={5} />);
    const rows = screen.getAllByRole("listitem");
    expect(rows).toHaveLength(5);
    // Last row is the aggregate of the 8 collapsed reasons.
    expect(rows[4]).toHaveTextContent("Other (8)");
  });

  it("renders a suffix and keeps hint as a title", () => {
    render(
      <HorizontalBarList
        items={[{ label: "Missing buyer identity", value: 2, hint: "missing_buyer_identity" }]}
        valueSuffix="batches"
      />,
    );
    const row = screen.getByRole("listitem");
    expect(row).toHaveTextContent("batches");
    expect(row).toHaveAttribute("title", "missing_buyer_identity");
  });

  it("renders the empty label when there are no items", () => {
    render(<HorizontalBarList items={[]} emptyLabel="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("has no axe violations", async () => {
    const { container } = render(
      <HorizontalBarList
        items={[{ label: "A", value: 3 }, { label: "B", value: 1 }]}
        ariaLabel="blockers"
      />,
    );
    const results = await axe(container);
    expect(results.violations).toEqual([]);
  });
});
