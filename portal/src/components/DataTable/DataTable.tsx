import { useRef, type KeyboardEvent, type ReactNode } from "react";
import clsx from "clsx";
import Skeleton from "../Skeleton/Skeleton";
import styles from "./DataTable.module.css";

export interface ColumnDef<T> {
  key: string;
  header: ReactNode;
  align?: "left" | "right";
  mono?: boolean;
  width?: string;
  render(row: T): ReactNode;
}

/**
 * Generic presentational table: sticky header, keyboard row navigation
 * (ArrowUp/Down move focus, Enter activates onRowClick), skeleton rows while
 * loading, and a designed empty state. No internal sorting or paging — the
 * parent supplies rows exactly as they should render.
 */
export default function DataTable<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  loading = false,
  empty,
  skeletonRows = 5,
}: {
  columns: ColumnDef<T>[];
  rows: T[];
  rowKey(row: T): string;
  onRowClick?(row: T): void;
  loading?: boolean;
  empty?: ReactNode;
  skeletonRows?: number;
}) {
  const bodyRef = useRef<HTMLTableSectionElement>(null);

  function onKeyDown(e: KeyboardEvent<HTMLTableRowElement>, row: T) {
    if (e.key === "Enter") {
      onRowClick?.(row);
      return;
    }
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
    e.preventDefault();
    const rowEls = Array.from(
      bodyRef.current?.querySelectorAll<HTMLTableRowElement>("tr[tabindex]") ??
        [],
    );
    const i = rowEls.indexOf(e.currentTarget);
    rowEls[e.key === "ArrowDown" ? i + 1 : i - 1]?.focus();
  }

  const showSkeleton = loading && rows.length === 0;
  const showEmpty = !loading && rows.length === 0;

  return (
    <table>
      <thead className={styles.stickyHead}>
        <tr>
          {columns.map((c) => (
            <th
              key={c.key}
              style={c.width ? { width: c.width } : undefined}
              className={clsx(c.align === "right" && styles.right)}
            >
              {c.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody ref={bodyRef}>
        {showSkeleton &&
          Array.from({ length: skeletonRows }).map((_, i) => (
            <tr key={i} data-testid="skeleton-row" className={styles.inert}>
              {columns.map((c) => (
                <td key={c.key}>
                  <Skeleton variant="text" />
                </td>
              ))}
            </tr>
          ))}
        {showEmpty && (
          <tr className={styles.inert}>
            <td colSpan={columns.length}>{empty ?? null}</td>
          </tr>
        )}
        {!showSkeleton &&
          rows.map((row) => (
            <tr
              key={rowKey(row)}
              tabIndex={0}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              onKeyDown={(e) => onKeyDown(e, row)}
            >
              {columns.map((c) => (
                <td
                  key={c.key}
                  className={clsx(
                    c.align === "right" && styles.right,
                    c.mono && "mono",
                  )}
                >
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
      </tbody>
    </table>
  );
}
