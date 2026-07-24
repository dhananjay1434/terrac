/**
 * Generic, reusable inline SVG bar chart — no charting dependency, no domain
 * knowledge. Follows the TemperatureChart pattern: fixed viewBox, theme CSS
 * vars for gridlines/fills, and per-element <title> children for native
 * browser hover tooltips.
 */
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
}

const WIDTH = 600;
const GRIDLINE_COUNT = 4;
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

export default function BarChart({
  data,
  height = 200,
  formatValue,
  emptyLabel,
  ariaLabel,
}: BarChartProps) {
  const label = ariaLabel ?? "bar chart";

  if (!data || data.length === 0) {
    return (
      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={label}
      >
        <text x="50%" y="50%" textAnchor="middle" className="micro">
          {emptyLabel ?? "No data"}
        </text>
      </svg>
    );
  }

  const format = formatValue ?? ((n: number) => String(n));
  const rawMax = Math.max(...data.map((d) => d.value));
  const max = rawMax > 0 ? rawMax * 1.1 : 1;

  const chartHeight = height - 20; // reserve space for x-axis labels
  const { slotWidth, barWidth } = computeLayout(data.length, WIDTH);
  const labelIndices = pickLabelIndices(data.length, MAX_X_LABELS);

  const gridlines = Array.from({ length: GRIDLINE_COUNT }, (_, i) => {
    const y = (chartHeight / (GRIDLINE_COUNT - 1)) * i;
    return (
      <line
        key={i}
        x1={0}
        y1={y}
        x2={WIDTH}
        y2={y}
        stroke="var(--border-subtle)"
        strokeWidth={1}
        opacity={0.45}
      />
    );
  });

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={label}
    >
      {gridlines}
      {data.map((d, i) => {
        const x = i * slotWidth + (slotWidth - barWidth) / 2;
        const rawBarHeight = (d.value / max) * chartHeight;
        // A true-zero (or otherwise tiny) value must still render a visible,
        // queryable bar rather than being silently dropped from the chart.
        const barHeight = Math.max(rawBarHeight, 2);
        const y = chartHeight - barHeight;
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
            {d.label}
          </text>
        );
      })}
    </svg>
  );
}
