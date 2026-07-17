import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";
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
 * Generic presentational table: sticky header, keyboard row navigation via
 * roving tabindex (the table is ONE tab stop; ArrowUp/Down/Home/End move
 * focus within it, Enter/Space activate onRowClick), skeleton rows while
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
  const [activeKey, setActiveKey] = useState<string | null>(null);

  function focusRow(i: number) {
    const rowEls = Array.from(
      bodyRef.current?.querySelectorAll<HTMLTableRowElement>(
        "tr[data-row-key]",
      ) ?? [],
    );
    const clamped = Math.max(0, Math.min(i, rowEls.length - 1));
    const el = rowEls[clamped];
    if (!el) return;
    setActiveKey(el.dataset.rowKey ?? null);
    el.focus();
  }

  function onKeyDown(e: KeyboardEvent<HTMLTableRowElement>, row: T) {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onRowClick?.(row);
      return;
    }
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(e.key)) return;
    e.preventDefault();
    const rowEls = Array.from(
      bodyRef.current?.querySelectorAll<HTMLTableRowElement>(
        "tr[data-row-key]",
      ) ?? [],
    );
    const i = rowEls.indexOf(e.currentTarget);
    if (e.key === "Home") return focusRow(0);
    if (e.key === "End") return focusRow(rowEls.length - 1);
    focusRow(e.key === "ArrowDown" ? i + 1 : i - 1);
  }

  const showSkeleton = loading && rows.length === 0;
  const showEmpty = !loading && rows.length === 0;

  return (
    <table aria-busy={loading}>
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
          rows.map((row, i) => {
            const key = rowKey(row);
            const isActive = activeKey === null ? i === 0 : activeKey === key;
            return (
              <tr
                key={key}
                data-row-key={key}
                tabIndex={isActive ? 0 : -1}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onFocus={() => setActiveKey(key)}
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
            );
          })}
      </tbody>
    </table>
  );
}
