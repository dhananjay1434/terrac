/**
 * Generic, reusable inline SVG bar chart — no charting dependency, no domain
 * knowledge. Follows the TemperatureChart pattern: fixed viewBox, theme CSS
 * vars for gridlines/fills, and per-element <title> children for native
 * browser hover tooltips.
 */
import { useLayoutEffect, useRef, useState } from "react";
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

// Coordinate-space width used until the container is measured (jsdom tests, SSR,
// and the first paint before layout). Once measured we use the real pixel width
// so 1 SVG unit == 1 CSS pixel — see useContainerWidth.
const FALLBACK_WIDTH = 600;
const GRIDLINE_COUNT = 4;
const MAX_X_LABELS = 8;

/**
 * Measures the host element's rendered pixel width so the SVG's viewBox can be
 * that same width (a 1:1 coordinate space). This is the fix for a stretched-SVG
 * dilemma: with a fixed 600-wide viewBox on a wider card, `preserveAspectRatio`
 * either letterboxes (default "meet" → dead gutters left/right) or distorts every
 * <text> label ("none" → glyphs stretched by cardWidth/600). Matching the viewBox
 * to the real width sidesteps both: bars fill the card AND text stays crisp, at
 * any width or bar count. Falls back to FALLBACK_WIDTH where layout is
 * unavailable (jsdom has no ResizeObserver; clientWidth is 0).
 */
function useContainerWidth(): [React.RefObject<HTMLDivElement>, number] {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(FALLBACK_WIDTH);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const w = el.clientWidth;
      if (w > 0) setWidth(w);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

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

export default function BarChart({
  data,
  height = 200,
  formatValue,
  emptyLabel,
  ariaLabel,
  showValues = false,
}: BarChartProps) {
  const label = ariaLabel ?? "bar chart";
  const [wrapRef, WIDTH] = useContainerWidth();

  if (!data || data.length === 0) {
    return (
      <div ref={wrapRef} className={styles.wrap}>
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
      </div>
    );
  }

  const format = formatValue ?? ((n: number) => String(n));
  const rawMax = Math.max(...data.map((d) => d.value));
  const max = rawMax > 0 ? rawMax * 1.1 : 1;

  const chartHeight = height - 20; // reserve space for x-axis labels
  const { slotWidth, barWidth } = computeLayout(data.length, WIDTH);
  const labelIndices = pickLabelIndices(data.length, MAX_X_LABELS);
  // Shown labels are spaced `step` slots apart — that's the real horizontal
  // room each one has before it would collide with the next shown label.
  const labelStep = Math.max(1, Math.ceil(data.length / MAX_X_LABELS));
  const labelBudget = slotWidth * labelStep * 0.9;

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
    <div ref={wrapRef} className={styles.wrap}>
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
        {showValues &&
          data.map((d, i) => {
            const rawBarHeight = (d.value / max) * chartHeight;
            const barHeight = Math.max(rawBarHeight, 2);
            const barTop = chartHeight - barHeight;
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
      </svg>
    </div>
  );
}
