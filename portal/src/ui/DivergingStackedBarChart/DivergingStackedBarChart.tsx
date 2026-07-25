/**
 * Generic, reusable inline SVG diverging stacked bar chart — no charting
 * dependency, no domain knowledge. The caller supplies colors, labels, and
 * tooltip rows; this component knows only geometry + a floating tooltip.
 * A separate, standalone sibling to `ui/BarChart` (that one is single-series
 * with a native <title> tooltip; this one stacks above/below a zero baseline
 * with a styled floating panel) — do not conflate the two.
 */
import { useState } from "react";
import styles from "./DivergingStackedBarChart.module.css";

export type StackSegment = { label: string; value: number; color: string };
export type DivergingBar = {
  label: string;
  above: StackSegment[];
  below: StackSegment[];
  tooltip: { label: string; value: number; bold?: boolean }[];
};

export interface DivergingStackedBarChartProps {
  data: DivergingBar[];
  height?: number;
  formatValue?: (n: number) => string;
  emptyLabel?: string;
  ariaLabel?: string;
}

const WIDTH = 720;
const LABEL_RESERVE = 24;
const MAX_X_LABELS = 8;

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

/** Lays out one side (above or below) of a bar's stack as {y, height} rects. */
function stackSegments(
  segments: StackSegment[],
  zeroY: number,
  pixelsPerUnit: number,
  direction: "up" | "down",
): { y: number; height: number; color: string; label: string; value: number }[] {
  const rects: { y: number; height: number; color: string; label: string; value: number }[] = [];
  let offset = 0;
  for (const seg of segments) {
    if (seg.value <= 0) continue;
    const h = Math.max(seg.value * pixelsPerUnit, 1);
    const y = direction === "up" ? zeroY - offset - h : zeroY + offset;
    rects.push({ y, height: h, color: seg.color, label: seg.label, value: seg.value });
    offset += h;
  }
  return rects;
}

export default function DivergingStackedBarChart({
  data,
  height = 240,
  formatValue,
  emptyLabel,
  ariaLabel,
}: DivergingStackedBarChartProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const label = ariaLabel ?? "chart";
  const format = formatValue ?? ((n: number) => String(n));

  if (!data || data.length === 0) {
    return (
      <svg viewBox={`0 0 ${WIDTH} ${height}`} width="100%" height={height} role="img" aria-label={label}>
        <text x="50%" y="50%" textAnchor="middle" className="micro">
          {emptyLabel ?? "No data"}
        </text>
      </svg>
    );
  }

  const plotHeight = height - LABEL_RESERVE;
  const zeroY = plotHeight / 2;
  const maxAbove = Math.max(...data.map((d) => d.above.reduce((s, seg) => s + seg.value, 0)), 0);
  const maxBelow = Math.max(...data.map((d) => d.below.reduce((s, seg) => s + seg.value, 0)), 0);
  const maxMag = Math.max(maxAbove, maxBelow, 1);
  const pixelsPerUnit = zeroY / maxMag;

  const barSlot = WIDTH / data.length;
  const barWidth = barSlot * 0.6;
  const labelIndices = pickLabelIndices(data.length, MAX_X_LABELS);

  const hoveredBar = hovered !== null ? data[hovered] : null;
  const tooltipFromRight = hovered !== null && hovered >= data.length - 2;

  return (
    <div style={{ position: "relative" }}>
      {/* role="group" (not "img") — this SVG contains focusable interactive
          hit-areas, and ARIA forbids nesting interactive controls inside an
          "img"-roled element. */}
      <svg viewBox={`0 0 ${WIDTH} ${height}`} width="100%" height={height} role="group" aria-label={label}>
        <line
          x1={0}
          y1={zeroY}
          x2={WIDTH}
          y2={zeroY}
          stroke="var(--border-subtle)"
          strokeWidth={1}
        />
        {data.map((bar, i) => {
          const x = i * barSlot + (barSlot - barWidth) / 2;
          const aboveRects = stackSegments(bar.above, zeroY, pixelsPerUnit, "up");
          const belowRects = stackSegments(bar.below, zeroY, pixelsPerUnit, "down");
          return (
            <g key={`${bar.label}-${i}`}>
              {[...aboveRects, ...belowRects].map((r, si) => (
                <rect
                  key={si}
                  x={x}
                  y={r.y}
                  width={barWidth}
                  height={r.height}
                  fill={r.color}
                />
              ))}
            </g>
          );
        })}
        {data.map((bar, i) => {
          if (!labelIndices.has(i)) return null;
          const x = i * barSlot + barSlot / 2;
          return (
            <text
              key={`label-${bar.label}-${i}`}
              x={x}
              y={height - 4}
              textAnchor="middle"
              className="micro"
            >
              {bar.label}
            </text>
          );
        })}
        {data.map((_, i) => (
          <rect
            key={`hit-${i}`}
            data-hit-area="true"
            x={i * barSlot}
            y={0}
            width={barSlot}
            height={plotHeight}
            fill="transparent"
            tabIndex={0}
            role="button"
            aria-label={data[i].label}
            onMouseEnter={() => setHovered(i)}
            onMouseLeave={() => setHovered(null)}
            onFocus={() => setHovered(i)}
            onBlur={() => setHovered(null)}
          />
        ))}
      </svg>
      {hoveredBar && (
        <div
          className={styles.tooltip}
          style={
            tooltipFromRight
              ? { right: `${((data.length - 1 - hovered!) / data.length) * 100}%`, top: 0 }
              : { left: `${(hovered! / data.length) * 100}%`, top: 0 }
          }
        >
          <div className={styles.tooltipHeader}>{hoveredBar.label}</div>
          {hoveredBar.tooltip.map((row, i) => (
            <div key={i} className={row.bold ? styles.tooltipRowBold : styles.tooltipRow}>
              <span>{row.label}</span>
              <span>{format(row.value)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
