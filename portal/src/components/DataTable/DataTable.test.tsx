import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import DataTable, { type ColumnDef } from "./DataTable";

type Row = { id: string; name: string };
const columns: ColumnDef<Row>[] = [
  { key: "name", header: "Name", render: (r) => r.name },
];
const rows: Row[] = [
  { id: "1", name: "alpha" },
  { id: "2", name: "beta" },
];

describe("DataTable", () => {
  it("renders rows", () => {
    render(<DataTable columns={columns} rows={rows} rowKey={(r) => r.id} />);
    expect(screen.getByText("alpha")).toBeInTheDocument();
    expect(screen.getByText("beta")).toBeInTheDocument();
  });

  it("renders skeleton rows while loading with no data", () => {
    render(
      <DataTable columns={columns} rows={[]} rowKey={(r: Row) => r.id} loading />,
    );
    expect(screen.getAllByTestId("skeleton-row").length).toBeGreaterThan(0);
  });

  it("renders the empty node when there are no rows", () => {
    render(
      <DataTable
        columns={columns}
        rows={[]}
        rowKey={(r: Row) => r.id}
        empty={<div>nothing</div>}
      />,
    );
    expect(screen.getByText("nothing")).toBeInTheDocument();
  });

  it("supports keyboard navigation and Enter to activate", () => {
    const onRowClick = vi.fn();
    render(
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(r) => r.id}
        onRowClick={onRowClick}
      />,
    );
    const first = screen.getByText("alpha").closest("tr")!;
    const second = screen.getByText("beta").closest("tr")!;
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowDown" });
    expect(document.activeElement).toBe(second);
    fireEvent.keyDown(second, { key: "ArrowUp" });
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first, { key: "Enter" });
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });
});
