import type { ReactNode } from "react";
import clsx from "clsx";
import styles from "./StatBand.module.css";

export interface StatBandProps {
  children: ReactNode;
  className?: string;
}

/** Responsive grid for a row of StatTiles (4-up desktop, 2-up ≤720px).
 * Matches the existing `.stat-band` CSS class via tokens. A thin wrapper
 * component so callers don't hand-type the class name. */
export default function StatBand({ children, className }: StatBandProps) {
  return <div className={clsx(styles.band, className)}>{children}</div>;
}
