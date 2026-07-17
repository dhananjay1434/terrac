import styles from "./MetricBlock.module.css";

/**
 * Numeric authority block: tabular-nums value + unit + caption. Sizes map to
 * the type-scale tokens. No count-up animation — static numbers read as more
 * trustworthy for financial figures (and reduced-motion users see the same).
 */
export default function MetricBlock({
  value,
  unit,
  caption,
  size = "lg",
}: {
  value: string;
  unit: string;
  caption?: string;
  size?: "sm" | "md" | "lg";
}) {
  return (
    <div className={styles.block} data-size={size}>
      <div className={styles.valueRow}>
        <span className={`${styles.value} tabular`}>{value}</span>
        <span className={styles.unit}>{unit}</span>
      </div>
      {caption && <div className={styles.caption}>{caption}</div>}
    </div>
  );
}
