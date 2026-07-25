import styles from "./HorizontalBarList.module.css";

export type BarListItem = {
  /** Human-readable label shown to the user. */
  label: string;
  value: number;
  /** Optional raw code / detail surfaced on hover (title). */
  hint?: string;
};

export interface HorizontalBarListProps {
  items: BarListItem[];
  /** Cap the rows shown; the remainder collapses into one "Other" row so the
   * list never turns into a barcode. Default 10. */
  maxItems?: number;
  /** Formats the numeric value (default: as-is). */
  formatValue?: (n: number) => string;
  /** Muted suffix after each value, e.g. "batches". */
  valueSuffix?: string;
  emptyLabel?: string;
  ariaLabel?: string;
}

/**
 * Generic horizontal ranked bar list ("bar-table"): one row per category,
 * label read left-to-right at full width (no rotation/truncation), an inline
 * indigo magnitude bar, and the exact value labeled at the right. This is the
 * canonical layout for a ranked breakdown of long-named categories where the
 * reader needs both the ranking AND the precise count (e.g. compliance
 * blockers) — a vertical bar chart truncates the labels and hides the counts.
 *
 * Domain-agnostic: the caller supplies already-humanized labels and the raw
 * code as `hint`. Colors come from brand indigo tokens; the single top row is
 * emphasized only when it's a strict leader, so a flat (all-equal) breakdown
 * isn't given a misleading standout.
 */
export default function HorizontalBarList({
  items,
  maxItems = 10,
  formatValue,
  valueSuffix,
  emptyLabel,
  ariaLabel,
}: HorizontalBarListProps) {
  const format = formatValue ?? ((n: number) => String(n));

  if (!items || items.length === 0) {
    return (
      <div className={styles.empty} role="note">
        {emptyLabel ?? "No data"}
      </div>
    );
  }

  const sorted = [...items].sort((a, b) => b.value - a.value);

  // Collapse the long tail into a single "Other" row past maxItems so the list
  // stays scannable. Summed count is honest; the collapsed codes go in the hint.
  let rows = sorted;
  if (sorted.length > maxItems) {
    const head = sorted.slice(0, maxItems - 1);
    const tail = sorted.slice(maxItems - 1);
    rows = [
      ...head,
      {
        label: `Other (${tail.length})`,
        value: tail.reduce((s, r) => s + r.value, 0),
        hint: tail.map((r) => r.hint ?? r.label).join(", "),
      },
    ];
  }

  const max = Math.max(...rows.map((r) => r.value), 1);
  // Emphasize the leader only when it's a STRICT leader — a flat breakdown
  // (every reason equally common) gets no misleading standout.
  const emphasizeTop = rows.length > 1 && rows[0].value > rows[1].value;

  return (
    <ul className={styles.list} role="list" aria-label={ariaLabel}>
      {rows.map((r, i) => {
        const pct = Math.max((r.value / max) * 100, 2);
        const isTop = i === 0 && emphasizeTop;
        return (
          <li key={`${r.label}-${i}`} className={styles.row} title={r.hint}>
            <div className={styles.head}>
              <span className={styles.label}>{r.label}</span>
              <span className={styles.value}>
                {format(r.value)}
                {valueSuffix ? <span className={styles.suffix}> {valueSuffix}</span> : null}
              </span>
            </div>
            <div className={styles.track}>
              <div
                className={styles.fill}
                data-top={isTop}
                style={{ width: `${pct}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
