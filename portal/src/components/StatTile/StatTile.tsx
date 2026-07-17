import styles from "./StatTile.module.css";

/**
 * Small presentational stat tile: label, a tabular-nums value, and an
 * optional hint line (e.g. to disclose a value's scope, like "loaded rows").
 */
export default function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="card">
      <span className="micro">{label}</span>
      <div className={`${styles.value} tabular`}>{value}</div>
      {hint && <div className={styles.hint}>{hint}</div>}
    </div>
  );
}
