import { useState } from "react";
import type { HierarchyNetwork } from "../../apiV2types";
import styles from "./FilterBar.module.css";

export interface FilterState {
  search: string;
  status: string;
  provisional: string;
}

export interface HierarchySelection {
  network_id?: string;
  site_id?: string;
  kiln_id?: string;
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
  hierarchy,
  onHierarchySelect,
}: {
  value: FilterState;
  onChange(patch: FilterPatch): void;
  // M1.5 (hierarchy_v2): optional cascading network→site→kiln filters. Rendered
  // only when the parent supplies non-empty hierarchy data (fed by the flagged
  // /hierarchy endpoint via api2.ts in M2.6). Absent data → no extra controls.
  hierarchy?: HierarchyNetwork[];
  onHierarchySelect?(sel: HierarchySelection): void;
}) {
  const [netId, setNetId] = useState("");
  const [siteId, setSiteId] = useState("");
  const [kilnId, setKilnId] = useState("");

  const hasHierarchy = !!hierarchy && hierarchy.length > 0;
  const net = hierarchy?.find((n) => n.network_id === netId);
  const site = net?.sites.find((s) => s.site_id === siteId);

  function emit(next: HierarchySelection) {
    onHierarchySelect?.(next);
  }

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
          <option value="RECEIVED">Received</option>
          <option value="ISSUED">Issued</option>
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
      {hasHierarchy && (
        <>
          <span className="select-wrap">
            <select
              aria-label="Filter by network"
              value={netId}
              onChange={(e) => {
                const v = e.target.value;
                setNetId(v);
                setSiteId("");
                setKilnId("");
                emit({ network_id: v || undefined });
              }}
            >
              <option value="">All networks</option>
              {hierarchy!.map((n) => (
                <option key={n.network_id} value={n.network_id}>
                  {n.name}
                </option>
              ))}
            </select>
          </span>
          {net && net.sites.length > 0 && (
            <span className="select-wrap">
              <select
                aria-label="Filter by site"
                value={siteId}
                onChange={(e) => {
                  const v = e.target.value;
                  setSiteId(v);
                  setKilnId("");
                  emit({ network_id: netId || undefined, site_id: v || undefined });
                }}
              >
                <option value="">All sites</option>
                {net.sites.map((s) => (
                  <option key={s.site_id} value={s.site_id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </span>
          )}
          {site && site.kilns.length > 0 && (
            <span className="select-wrap">
              <select
                aria-label="Filter by kiln"
                value={kilnId}
                onChange={(e) => {
                  const v = e.target.value;
                  setKilnId(v);
                  emit({
                    network_id: netId || undefined,
                    site_id: siteId || undefined,
                    kiln_id: v || undefined,
                  });
                }}
              >
                <option value="">All kilns</option>
                {site.kilns.map((k) => (
                  <option key={k.kiln_id} value={k.kiln_id}>
                    {k.kiln_code ?? k.kiln_id}
                  </option>
                ))}
              </select>
            </span>
          )}
        </>
      )}
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
