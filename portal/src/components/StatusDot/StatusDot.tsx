import styles from "./StatusDot.module.css";

export type StatusDotVariant = "success" | "warning" | "error" | "inert";

/**
 * 8px semantic status dot with optional label. Color comes exclusively from
 * the semantic status tokens; the label repeats the state in text so color
 * is never the sole indicator.
 */
export default function StatusDot({
  variant,
  label,
}: {
  variant: StatusDotVariant;
  label?: string;
}) {
  return (
    <span className={styles.wrap} data-variant={variant}>
      <span className={styles.dot} aria-hidden />
      {label && <span>{label}</span>}
    </span>
  );
}
