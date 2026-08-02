import styles from "./ChartTooltip.module.css";

export interface TooltipItem {
  label: string;
  color: string;
  value: string;
}
/** One consistent tooltip box for every chart. `xFrac` is the fraction across the
 * PLOT (not the wrapper). The plot is inset by ChartFrame's y-axis gutter (44px —
 * see §0.7 AXIS_GUTTER), so we position with that same inset or the tooltip won't
 * line up with the crosshair. It flips left of the cursor past the midpoint so it
 * never runs off the right edge. Presentational only. */
const AXIS_GUTTER_PX = 44; // MUST equal ChartFrame's AXIS_GUTTER (§0.7)
export default function ChartTooltip({
  label,
  items,
  xFrac,
}: {
  label: string;
  items: TooltipItem[];
  xFrac: number;
}) {
  const flip = xFrac > 0.6;
  return (
    <div
      className={styles.tip}
      style={{
        left: `calc(${AXIS_GUTTER_PX}px + ${xFrac} * (100% - ${AXIS_GUTTER_PX}px))`,
        transform: flip ? "translateX(calc(-100% - 10px))" : "translateX(10px)",
      }}
      role="status"
    >
      <div className={`micro ${styles.label}`}>{label}</div>
      {items.map((it) => (
        <div key={it.label} className={styles.row}>
          <span className={styles.dot} style={{ background: it.color }} />
          <span className="micro">{it.label}</span>
          <span className="mono tabular">{it.value}</span>
        </div>
      ))}
    </div>
  );
}
