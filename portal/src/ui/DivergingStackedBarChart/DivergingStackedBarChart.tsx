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

/** Distinct segment labels across all bars on one side, in first-seen order. */
function collectLabels(bars: DivergingBar[], side: "above" | "below"): string[] {
  const labels: string[] = [];
  const seen = new Set<string>();
  for (const bar of bars) {
    for (const seg of bar[side]) {
      if (!seen.has(seg.label)) {
        seen.add(seg.label);
        labels.push(seg.label);
      }
    }
  }
  return labels;
}

/** Each label's own max value across all bars, on one side. */
function maxByLabel(bars: DivergingBar[], side: "above" | "below"): Map<string, number> {
  const max = new Map<string, number>();
  for (const bar of bars) {
    for (const seg of bar[side]) {
      max.set(seg.label, Math.max(max.get(seg.label) ?? 0, seg.value));
    }
  }
  return max;
}

/**
 * Per-label pixels-per-unit: divides the available half-height into one
 * equal-sized lane per distinct label, then scales that label's values
 * against its OWN max — never a shared max across labels. Net credit and
 * its deductions (or several deduction categories against each other) can
 * differ by orders of magnitude in real methodology data; without this, a
 * small-but-real category (e.g. transport) would be an invisible sliver
 * next to a larger one (e.g. safety margin) even after the exact figures
 * are preserved in the tooltip. A label whose value is genuinely zero in
 * every bar gets no lane budget used — zero stays zero, never fabricated.
 */
function pixelsPerUnitByLabel(bars: DivergingBar[], side: "above" | "below", laneHeight: number): Map<string, number> {
  const labels = collectLabels(bars, side);
  const maxes = maxByLabel(bars, side);
  const lane = laneHeight / Math.max(labels.length, 1);
  const result = new Map<string, number>();
  for (const label of labels) {
    const labelMax = maxes.get(label) ?? 0;
    result.set(label, labelMax > 0 ? lane / labelMax : 0);
  }
  return result;
}

/** Lays out one side (above or below) of a bar's stack as {y, height} rects. */
function stackSegments(
  segments: StackSegment[],
  zeroY: number,
  ppuByLabel: Map<string, number>,
  direction: "up" | "down",
): { y: number; height: number; color: string; label: string; value: number }[] {
  const rects: { y: number; height: number; color: string; label: string; value: number }[] = [];
  let offset = 0;
  for (const seg of segments) {
    if (seg.value <= 0) continue;
    const ppu = ppuByLabel.get(seg.label) ?? 0;
    const h = Math.max(seg.value * ppu, 2);
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
  // Above and below each get their own half-height, subdivided further into
  // one lane per distinct label — so every real, non-zero category (net
  // credit, safety margin, transport, CH4, ...) is scaled against its own
  // max and gets equal visual weight, rather than the largest category
  // (net credit above; whichever deduction happens to be biggest below)
  // swamping the rest. Exact figures are unchanged and always in the
  // tooltip — only the relative visual proportion is a chart convention.
  const ppuAboveByLabel = pixelsPerUnitByLabel(data, "above", zeroY);
  const ppuBelowByLabel = pixelsPerUnitByLabel(data, "below", plotHeight - zeroY);

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
          const aboveRects = stackSegments(bar.above, zeroY, ppuAboveByLabel, "up");
          const belowRects = stackSegments(bar.below, zeroY, ppuBelowByLabel, "down");
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
