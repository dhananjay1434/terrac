import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import FilterBar, { type FilterPatch } from "./FilterBar";

const value = { search: "", status: "", provisional: "" };

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
});
