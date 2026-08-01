import type { ReactNode } from "react";
import styles from "./CellStack.module.css";

/** Two-line table cell: a bold primary line over a muted secondary line
 * (name + location, date + time, network + kiln…). The single highest-impact
 * table pattern — pure and prop-driven. */
export default function CellStack({
  primary,
  secondary,
}: {
  primary: ReactNode;
  secondary?: ReactNode;
}) {
  return (
    <span className={styles.stack}>
      <span className={styles.primary}>{primary}</span>
      {secondary != null && secondary !== "" && (
        <span className={styles.secondary}>{secondary}</span>
      )}
    </span>
  );
}
