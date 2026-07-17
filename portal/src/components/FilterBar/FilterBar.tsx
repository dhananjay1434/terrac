import styles from "./FilterBar.module.css";

export interface FilterState {
  search: string;
  status: string;
  provisional: string;
}

/** Discriminated union of everything the bar can emit — parent owns state. */
export type FilterPatch =
  | { kind: "search"; value: string }
  | { kind: "status"; value: string }
  | { kind: "provisional"; value: string }
  | { kind: "clear" };

/**
 * Stateless filter bar: search text (client-side), the two server-side
 * selects, and clear-all. Emits FilterPatch events; the parent applies them
 * and owns defaults (e.g. per saved view).
 */
export default function FilterBar({
  value,
  onChange,
}: {
  value: FilterState;
  onChange(patch: FilterPatch): void;
}) {
  return (
    <div className={styles.bar}>
      <input
        className={styles.search}
        aria-label="Filter loaded rows by batch or device"
        placeholder="Filter loaded rows…"
        value={value.search}
        onChange={(e) => onChange({ kind: "search", value: e.target.value })}
      />
      <span className="select-wrap">
        <select
          aria-label="Filter by status"
          value={value.status}
          onChange={(e) => onChange({ kind: "status", value: e.target.value })}
        >
          <option value="">All statuses</option>
          <option value="RECEIVED">RECEIVED</option>
          <option value="ISSUED">ISSUED</option>
        </select>
      </span>
      <span className="select-wrap">
        <select
          aria-label="Filter by eligibility"
          value={value.provisional}
          onChange={(e) =>
            onChange({ kind: "provisional", value: e.target.value })
          }
        >
          <option value="">Provisional &amp; issuable</option>
          <option value="true">Provisional only</option>
          <option value="false">Issuable only</option>
        </select>
      </span>
      <button
        className="linkbtn"
        type="button"
        onClick={() => onChange({ kind: "clear" })}
      >
        Clear filters
      </button>
    </div>
  );
}
