import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import styles from "./ChartFrame.module.css";

// Coordinate width used until the container is measured (jsdom/SSR/first paint);
// then we use the real pixel width so 1 SVG unit == 1 CSS pixel (bars/lines fill
// the width AND text stays crisp — the responsive fix proven in BarChart).
const FALLBACK_WIDTH = 600;

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

export interface ChartLegendItem {
  label: string;
  color: string;
}
export interface ChartHeaderStat {
  label: string;
  value: string;
}
export interface ChartFrameProps {
  /** Accessible description of the whole chart. Required. */
  ariaLabel: string;
  /** [lo, hi] in data space — ChartFrame owns the y-scale so gridlines, labels,
   * and the marks the child draws all share ONE scale. */
  yDomain: [number, number];
  title?: string;
  badge?: ReactNode;
  headerStats?: ChartHeaderStat[];
  legend?: ChartLegendItem[];
  /** Visually-hidden summary (e.g. series + latest/peak) wired to the SVG via
   * aria-describedby, so screen-reader users get the numeric gist without
   * having to parse SVG marks. */
  summary?: string;
  height?: number;
  /** Data-space values to label on the y-axis. Defaults to 5 even ticks. */
  yTicks?: number[];
  yFormat?: (v: number) => string;
  /** Optional hover overlay. When provided, ChartFrame renders a transparent
   * pointer-capture rect over the plot and reports the pointer x as a fraction
   * [0,1] of plot width (null on leave). Charts that don't pass this are
   * unchanged (BarChart, TemperatureChart). */
  onHoverFrac?: (frac: number | null) => void;
  /** Fraction [0,1] of plot width at which to draw a 1px vertical crosshair, or
   * null for none. SYMMETRIC with onHoverFrac (report a fraction, accept a
   * fraction) so no chart ever juggles pixels — the caller derives this from the
   * shared hover TIME: `(hoverT - t0) / span`. */
  crosshairFrac?: number | null;
  /** The chart's marks, drawn in plot space: x in [0, w], y via yScale(value). */
  children: (plot: {
    w: number;
    h: number;
    yScale: (v: number) => number;
  }) => ReactNode;
}

const AXIS_GUTTER = 44; // left room for y-axis labels
const X_AXIS_H = 20; // bottom room (keeps a consistent baseline rhythm)
const PLOT_TOP = 8; // headroom so peaks never clip

// Below this measured width there isn't room for 5 evenly-spaced y-axis
// labels without them colliding — narrow chart cards get 3 instead.
const NARROW_WIDTH = 400;

function defaultTicks([lo, hi]: [number, number], width: number): number[] {
  if (hi <= lo) return [lo];
  const steps = width < NARROW_WIDTH ? 2 : 4;
  return Array.from(
    { length: steps + 1 },
    (_, i) => lo + ((hi - lo) / steps) * i,
  );
}

/**
 * Chart CHROME owned in one place: responsive 1:1 sizing, gridlines, y-axis
 * ticks + labels, a header (title / stat chips / badge), and a colored-dot
 * legend. Each chart supplies ONLY its marks via `children`, drawn in the plot
 * space ChartFrame hands back. No chart library — plain SVG.
 */
export default function ChartFrame({
  ariaLabel,
  yDomain,
  title,
  badge,
  headerStats,
  legend,
  summary,
  height = 200,
  yTicks,
  yFormat = (v) => v.toFixed(0),
  onHoverFrac,
  crosshairFrac = null,
  children,
}: ChartFrameProps) {
  const [wrapRef, width] = useContainerWidth();
  const summaryId = useId();
  const [lo, hi] = yDomain;
  const ticks = yTicks ?? defaultTicks(yDomain, width);

  const plotW = Math.max(width - AXIS_GUTTER, 1);
  const plotH = Math.max(height - X_AXIS_H - PLOT_TOP, 1);
  const yScale = (v: number) =>
    hi === lo
      ? PLOT_TOP + plotH / 2
      : PLOT_TOP + (1 - (v - lo) / (hi - lo)) * plotH;

  const hasHeader = Boolean(title || badge || (headerStats && headerStats.length));

  return (
    <div ref={wrapRef} className={styles.frame}>
      {hasHeader && (
        <div className={styles.head}>
          <div className={styles.headLeft}>
            {title && <span className="micro">{title}</span>}
          </div>
          <div className={styles.headRight}>
            {headerStats?.map((s) => (
              <span key={s.label} className={styles.stat}>
                <span className="micro">{s.label}</span>
                <span className="mono tabular">{s.value}</span>
              </span>
            ))}
            {badge && <span className={styles.badge}>{badge}</span>}
          </div>
        </div>
      )}
      {summary && (
        <span className={styles.visuallyHidden} id={summaryId}>
          {summary}
        </span>
      )}
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={ariaLabel}
        aria-describedby={summary ? summaryId : undefined}
      >
        {ticks.map((t) => {
          const y = yScale(t);
          return (
            <g key={t}>
              <line
                x1={AXIS_GUTTER}
                y1={y}
                x2={width}
                y2={y}
                stroke="var(--border-subtle)"
                strokeWidth={1}
                opacity={0.45}
              />
              <text
                x={AXIS_GUTTER - 6}
                y={y + 3}
                textAnchor="end"
                className={`micro ${styles.axisLabel}`}
              >
                {yFormat(t)}
              </text>
            </g>
          );
        })}
        <g transform={`translate(${AXIS_GUTTER} 0)`}>
          {children({ w: plotW, h: plotH, yScale })}
          {crosshairFrac != null && (
            <line
              data-crosshair="true"
              x1={crosshairFrac * plotW}
              y1={PLOT_TOP}
              x2={crosshairFrac * plotW}
              y2={PLOT_TOP + plotH}
              stroke="var(--text-tertiary, currentColor)"
              strokeWidth={1}
              opacity={0.6}
              pointerEvents="none"
            />
          )}
          {onHoverFrac && (
            <rect
              x={0}
              y={PLOT_TOP}
              width={plotW}
              height={plotH}
              fill="transparent"
              onPointerMove={(e) => {
                const r = (e.target as SVGRectElement).getBoundingClientRect();
                const f = r.width > 0 ? (e.clientX - r.left) / r.width : 0;
                onHoverFrac(Math.min(1, Math.max(0, f)));
              }}
              onPointerLeave={() => onHoverFrac(null)}
            />
          )}
        </g>
      </svg>
      {legend && legend.length > 0 && (
        <div className={styles.legend}>
          {legend.map((l) => (
            <span key={l.label} className={styles.legendItem}>
              <span className={styles.dot} style={{ background: l.color }} />
              <span className="micro">{l.label}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
