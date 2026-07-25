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
    const h = Math.max(seg.value * pixelsPerUnit, 2);
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
  // Above and below scale INDEPENDENTLY (each half fills its own half-height
  // based on its own max), not off one shared magnitude. Net credit and its
  // deductions differ by 1-2 orders of magnitude in the real methodology
  // (a compliant batch's safety/transport/CH4 penalties are meant to be
  // small) — a single shared scale would render deductions as an invisible
  // sliver. The exact figures are always in the tooltip; only the relative
  // above-vs-below visual proportion is a chart convention, not a data claim.
  const pixelsPerUnitAbove = zeroY / Math.max(maxAbove, 1);
  const pixelsPerUnitBelow = (plotHeight - zeroY) / Math.max(maxBelow, 1);

  const barSlot = WIDTH / data.length;
  // Denser packing (was 0.6) reads as a fuller, richer chart when there are
  // few bars — still leaves a clear gap so adjacent bars never touch.
  const barWidth = barSlot * 0.72;
  const labelIndices = pickLabelIndices(data.length, MAX_X_LABELS);

  const hoveredBar = hovered !== null ? data[hovered] : null;
  const tooltipFromRight = hovered !== null && hovered >= data.length - 2;

  return (
    <div style={{ position: "relative" }}>
      {/* role="group" (not "img") — this SVG contains focusable interactive
          hit-areas, and ARIA forbids nesting interactive controls inside an
          "img"-roled element. */}
      <svg viewBox={`0 0 ${WIDTH} ${height}`} width="100%" height={height} role="group" aria-label={label}>
        {/* Faint reference gridlines above and below zero, for chart texture
            — purely decorative, carry no additional data. */}
        {[0.5, 1].map((frac) => (
          <line
            key={`grid-above-${frac}`}
            x1={0}
            y1={zeroY - zeroY * frac}
            x2={WIDTH}
            y2={zeroY - zeroY * frac}
            stroke="var(--border-subtle)"
            strokeWidth={1}
            opacity={0.35}
          />
        ))}
        {[0.5, 1].map((frac) => (
          <line
            key={`grid-below-${frac}`}
            x1={0}
            y1={zeroY + (plotHeight - zeroY) * frac}
            x2={WIDTH}
            y2={zeroY + (plotHeight - zeroY) * frac}
            stroke="var(--border-subtle)"
            strokeWidth={1}
            opacity={0.35}
          />
        ))}
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
          const aboveRects = stackSegments(bar.above, zeroY, pixelsPerUnitAbove, "up");
          const belowRects = stackSegments(bar.below, zeroY, pixelsPerUnitBelow, "down");
          return (
            <g key={`${bar.label}-${i}`}>
              {aboveRects.map((r, si) => (
                <rect key={`above-${si}`} data-side="above" x={x} y={r.y} width={barWidth} height={r.height} fill={r.color} />
              ))}
              {belowRects.map((r, si) => (
                <rect key={`below-${si}`} data-side="below" x={x} y={r.y} width={barWidth} height={r.height} fill={r.color} />
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
