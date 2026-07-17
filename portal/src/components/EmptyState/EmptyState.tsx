import type { ReactNode } from "react";
import styles from "./EmptyState.module.css";

/**
 * Designed empty state: optional icon, 18px title, secondary description,
 * optional single action. Rendered inside table wells or cards.
 */
export default function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick(): void };
}) {
  return (
    <div className={styles.wrap}>
      {icon && <div className={styles.icon}>{icon}</div>}
      <div className={styles.title}>{title}</div>
      {description && <div className={styles.desc}>{description}</div>}
      {action && (
        <button className="neutral" type="button" onClick={action.onClick}>
          {action.label}
        </button>
      )}
    </div>
  );
}
