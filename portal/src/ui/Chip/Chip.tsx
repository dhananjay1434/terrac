import type { ReactNode } from "react";
import styles from "./Chip.module.css";

/** Plain labeled chip for a non-status value (e.g. a species, a category) —
 * no icon, no semantic tone. Use StatusPill instead when the value IS a
 * success/warning/error/inert state. `title` lets long values truncate
 * visually while staying available on hover/inspection. */
export default function Chip({ children, title }: { children: ReactNode; title?: string }) {
  return (
    <span className={styles.chip} title={title}>
      {children}
    </span>
  );
}
