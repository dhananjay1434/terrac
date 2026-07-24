import type { ReactNode } from "react";
import { Check, AlertTriangle, X, Minus } from "lucide-react";
import styles from "./StatusPill.module.css";

export type PillStatus = "success" | "warning" | "error" | "inert";

const ICON: Record<PillStatus, typeof Check> = {
  success: Check,
  warning: AlertTriangle,
  error: X,
  inert: Minus,
};

export interface StatusPillProps {
  status: PillStatus;
  children: ReactNode;
}

/** One component for all status rendering — tinted background, saturated
 * text, and an icon, so status is never conveyed by color alone. Matches
 * the existing `.chip.ok/.warn/.err` look via tokens. */
export default function StatusPill({ status, children }: StatusPillProps) {
  const Icon = ICON[status];
  return (
    <span className={`${styles.pill} ${styles[status]}`}>
      <Icon size={12} aria-hidden="true" />
      <span>{children}</span>
    </span>
  );
}
