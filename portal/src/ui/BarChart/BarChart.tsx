/**
 * Generic, reusable inline SVG bar chart — no charting dependency, no domain
 * knowledge. Follows the TemperatureChart pattern: fixed viewBox, theme CSS
 * vars for gridlines/fills, and per-element <title> children for native
 * browser hover tooltips.
 */
import ChartFrame from "../ChartFrame/ChartFrame";
import styles from "./BarChart.module.css";

export interface BarChartDatum {
  label: string;
  value: number;
}

export interface BarChartProps {
  data: BarChartDatum[];
  height?: number;
  formatValue?: (n: number) => string;
  emptyLabel?: string;
  ariaLabel?: string;
  /** Print each bar's value directly above it. For a distribution/histogram
   * this is the difference between "a tall bar and three slivers" and knowing
   * the exact count per bucket (incl. an explicit 0 for empty buckets). */
  showValues?: boolean;
}

const MAX_X_LABELS = 8;

/** Computes bar geometry (x position + width) for a given number of bars. */
function computeLayout(count: number, width: number) {
  const slotWidth = width / count;
  const barWidth = Math.max(slotWidth * 0.6, 1);
  return { slotWidth, barWidth };
}

/** Picks an evenly-spaced subset of indices, capped at maxLabels. */
function pickLabelIndices(count: number, maxLabels: number): Set<number> {
  const indices = new Set<number>();
  if (count <= maxLabels) {
    for (let i = 0; i < count; i += 1) indices.add(i);
    return indices;
  }
  const step = Math.ceil(count / maxLabels);
  for (let i = 0; i < count; i += step) indices.add(i);
  return indices;
}

// Rough average glyph width (px) for the `.micro` 12px label font — used only
// to decide how many characters fit in a slot before truncating. The full
// label always stays available in the bar's <title> tooltip.
const APPROX_CHAR_WIDTH = 6;

/** Truncates a label with an ellipsis if it wouldn't fit its slot width. */
function truncateLabel(label: string, slotWidth: number): string {
  const maxChars = Math.max(3, Math.floor(slotWidth / APPROX_CHAR_WIDTH));
  if (label.length <= maxChars) return label;
  return `${label.slice(0, maxChars - 1)}…`;
}

/** Compact y-axis tick formatter — ChartFrame's left gutter is sized for
 * short labels; a raw 6-digit magnitude (biomass kg, credit totals, ...)
 * would render past the SVG's left edge and clip. Abbreviate to "170.4k"
 * instead of the exact value — the precise figure is still in each bar's
 * <title> tooltip and its showValues label. */
function compactTick(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1000) {
    return `${(v / 1000).toLocaleString(undefined, { maximumFractionDigits: 1 })}k`;
  }
  return String(Math.round(v));
}

export default function BarChart({
  data,
  height = 200,
  formatValue,
  emptyLabel,
  ariaLabel,
  showValues = false,
}: BarChartProps) {
  const label = ariaLabel ?? "bar chart";

  if (!data || data.length === 0) {
    return (
      <div className={styles.wrap}>
        <ChartFrame ariaLabel={label} yDomain={[0, 1]} yTicks={[]} height={height}>
          {() => (
            <text x="50%" y="50%" textAnchor="middle" className="micro">
              {emptyLabel ?? "No data"}
            </text>
          )}
        </ChartFrame>
      </div>
    );
  }

  const format = formatValue ?? ((n: number) => String(n));
  const rawMax = Math.max(...data.map((d) => d.value));
  const max = rawMax > 0 ? rawMax * 1.1 : 1;

  const labelIndices = pickLabelIndices(data.length, MAX_X_LABELS);

  return (
    <div className={styles.wrap}>
      <ChartFrame ariaLabel={label} yDomain={[0, max]} yFormat={compactTick} height={height}>
        {({ w, yScale: yy }) => {
          const { slotWidth, barWidth } = computeLayout(data.length, w);
          // Shown labels are spaced `step` slots apart — that's the real horizontal
          // room each one has before it would collide with the next shown label.
          const labelStep = Math.max(1, Math.ceil(data.length / MAX_X_LABELS));
          const labelBudget = slotWidth * labelStep * 0.9;
          const baseline = yy(0);
          return (
            <>
              {data.map((d, i) => {
                const x = i * slotWidth + (slotWidth - barWidth) / 2;
                const rawBarHeight = baseline - yy(d.value);
                // A true-zero (or otherwise tiny) value must still render a visible,
                // queryable bar rather than being silently dropped from the chart.
                const barHeight = Math.max(rawBarHeight, 2);
                const y = baseline - barHeight;
                return (
                  <rect
                    key={`${d.label}-${i}`}
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill="var(--indigo-600)"
                  >
                    <title>
                      {d.label}: {format(d.value)}
                    </title>
                  </rect>
                );
              })}
              {showValues &&
                data.map((d, i) => {
                  // Only the same thinned set of indices used for x-axis labels —
                  // rendering a value label above EVERY bar collides into unreadable
                  // overlapping text once there are more than a handful of bars
                  // (e.g. a daily-bucketed chart with 79+ bars). At <= MAX_X_LABELS
                  // bars this is a no-op: labelIndices already contains every index.
                  if (!labelIndices.has(i)) return null;
                  const rawBarHeight = baseline - yy(d.value);
                  const barHeight = Math.max(rawBarHeight, 2);
                  const barTop = baseline - barHeight;
                  // Sit the value just above the bar; clamp so the tallest bar's
                  // label never clips past the top edge (the max*1.1 headroom leaves
                  // room, this is belt-and-suspenders).
                  const labelY = Math.max(barTop - 5, 10);
                  const cx = i * slotWidth + slotWidth / 2;
                  return (
                    <text
                      key={`value-${d.label}-${i}`}
                      x={cx}
                      y={labelY}
                      textAnchor="middle"
                      className={`micro ${styles.valueLabel}`}
                    >
                      {format(d.value)}
                    </text>
                  );
                })}
              {data.map((d, i) => {
                if (!labelIndices.has(i)) return null;
                const x = i * slotWidth + slotWidth / 2;
                return (
                  <text
                    key={`label-${d.label}-${i}`}
                    x={x}
                    y={height - 4}
                    textAnchor="middle"
                    className={`micro ${styles.axisLabel}`}
                  >
                    {truncateLabel(d.label, labelBudget)}
                  </text>
                );
              })}
            </>
          );
        }}
      </ChartFrame>
    </div>
  );
}
