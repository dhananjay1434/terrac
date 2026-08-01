import type { ReactNode } from "react";
import styles from "./Chip.module.css";

/** Plain labeled chip for a non-status value (e.g. a species, a category) —
 * no icon, no semantic tone. Use StatusPill instead when the value IS a
 * success/warning/error/inert state. */
export default function Chip({ children }: { children: ReactNode }) {
  return <span className={styles.chip}>{children}</span>;
}
