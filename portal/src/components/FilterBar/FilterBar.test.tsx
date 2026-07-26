import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FilterBar, { type FilterPatch } from "./FilterBar";
import type { HierarchyNetwork } from "../../apiV2types";

const value = { search: "", status: "", provisional: "" };

const HIERARCHY: HierarchyNetwork[] = [
  {
    network_id: "NET-1",
    name: "North Net",
    sites: [
      {
        site_id: "FAC-1",
        name: "Site A",
        kilns: [{ kiln_id: "KILN-1", kiln_code: "K01", sensor_profile: "full" }],
      },
    ],
  },
];

describe("FilterBar", () => {
  it("emits a search patch", () => {
    const onChange = vi.fn<(p: FilterPatch) => void>();
    render(<FilterBar value={value} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Filter loaded rows by batch or device"), {
      target: { value: "dev-1" },
    });
    expect(onChange).toHaveBeenCalledWith({ kind: "search", value: "dev-1" });
  });

  it("emits status and provisional patches", () => {
    const onChange = vi.fn<(p: FilterPatch) => void>();
    render(<FilterBar value={value} onChange={onChange} />);
    fireEvent.change(screen.getByLabelText("Filter by status"), {
      target: { value: "ISSUED" },
    });
    expect(onChange).toHaveBeenCalledWith({ kind: "status", value: "ISSUED" });
    fireEvent.change(screen.getByLabelText("Filter by eligibility"), {
      target: { value: "true" },
    });
    expect(onChange).toHaveBeenCalledWith({ kind: "provisional", value: "true" });
  });

  it("emits clear", () => {
    const onChange = vi.fn<(p: FilterPatch) => void>();
    render(<FilterBar value={value} onChange={onChange} />);
    fireEvent.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(onChange).toHaveBeenCalledWith({ kind: "clear" });
  });

  it("hides the hierarchy selects when no data is supplied (M1.5)", () => {
    render(<FilterBar value={value} onChange={vi.fn()} />);
    expect(screen.queryByLabelText("Filter by network")).not.toBeInTheDocument();
  });

  it("renders cascading network→site→kiln selects when hierarchy is present (M1.5)", () => {
    const onSel = vi.fn();
    render(
      <FilterBar
        value={value}
        onChange={vi.fn()}
        hierarchy={HIERARCHY}
        onHierarchySelect={onSel}
      />,
    );
    const network = screen.getByLabelText("Filter by network");
    // site/kiln hidden until a network is chosen
    expect(screen.queryByLabelText("Filter by site")).not.toBeInTheDocument();
    fireEvent.change(network, { target: { value: "NET-1" } });
    expect(onSel).toHaveBeenCalledWith({ network_id: "NET-1" });

    const site = screen.getByLabelText("Filter by site");
    fireEvent.change(site, { target: { value: "FAC-1" } });
    expect(onSel).toHaveBeenCalledWith({ network_id: "NET-1", site_id: "FAC-1" });
    expect(screen.getByLabelText("Filter by kiln")).toBeInTheDocument();
  });
});
