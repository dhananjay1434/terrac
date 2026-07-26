import { indigoTone } from "@config/chartPalette";
import styles from "./ThermalMapChart.module.css";

/**
 * Multi-channel burn thermal map (M2.7). Renders up to 4 thermocouple series
 * (T1–T4) from live/stored telemetry, hand-built SVG (no chart lib — matches
 * the TemperatureChart geometry lessons: preserveAspectRatio="none", y padded
 * to [8, 192] so peaks/troughs never clip).
 *
 * Tier-aware (Global Rule 10): renders exactly the channels present. One probe
 * → one line; zero channels → returns null so the parent falls back to the
 * legacy app-evidence chart. Never draws placeholder series, never shows a
 * "sensor missing" warning — absence of sensors is a normal tier, not an error.
 *
 * Gaps are rendered as literal breaks in the line + a "sensor gap" annotation
 * — never interpolated (audit A4: absence is evidence).
 */
export interface ChannelSeries {
  points: [number, number][]; // [epoch_ms, value]
  max: number;
  min: number;
}
export interface ThermalMapData {
  channels: Record<string, ChannelSeries>; // keyed "T1".."T4"
  burn: { t_start: number; t_end: number; gaps?: [number, number][] };
}

const VIEW_W = 600;
const VIEW_H = 200;
const Y_TOP = 8;
const Y_BOT = 192;
const CHANNEL_ORDER = ["T1", "T2", "T3", "T4"] as const;

function yScale(v: number, lo: number, hi: number): number {
  if (hi === lo) return (Y_TOP + Y_BOT) / 2;
  return Y_BOT - ((v - lo) / (hi - lo)) * (Y_BOT - Y_TOP);
}

/** Split a series into contiguous segments, breaking across any burn gap so we
 * never draw a line through a sensor outage. */
function segments(
  points: [number, number][],
  gaps: [number, number][],
): [number, number][][] {
  if (points.length === 0) return [];
  const out: [number, number][][] = [];
  let cur: [number, number][] = [];
  for (const p of points) {
    const inGap = gaps.some(([g0, g1]) => p[0] > g0 && p[0] < g1);
    if (inGap) {
      if (cur.length) out.push(cur);
      cur = [];
    } else {
      cur.push(p);
    }
  }
  if (cur.length) out.push(cur);
  return out;
}

export default function ThermalMapChart({
  data,
  gateSatisfied = false,
}: {
  data: ThermalMapData;
  /** Whether the sustained-temperature compliance gate has passed. Colors the
   * MAX badge — the compliance tie-in a plain chart lacks. Computed by the
   * caller (backend/credit engine), never by this presentational component. */
  gateSatisfied?: boolean;
}) {
  const present = CHANNEL_ORDER.filter((c) => data.channels[c]?.points.length);
  if (present.length === 0) return null; // Tier-aware: nothing to draw

  const allValues = present.flatMap((c) => data.channels[c].points.map((p) => p[1]));
  const lo = Math.min(...allValues);
  const hi = Math.max(...allValues);
  const peak = Math.max(...present.map((c) => data.channels[c].max));

  const t0 = data.burn.t_start;
  const span = (data.burn.t_end || t0) - t0 || 1; // guard zero-span burns
  const xScale = (t: number) => ((t - t0) / span) * VIEW_W;
  const gaps = data.burn.gaps ?? [];

  const gridY = [Y_TOP, (Y_TOP + Y_BOT) / 2, Y_BOT];

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <span className="micro">Burn thermal map</span>
        <span
          className={styles.maxBadge}
          data-gate={gateSatisfied ? "pass" : "pending"}
        >
          MAX <span className="mono tabular">{peak.toFixed(1)}</span>°C
        </span>
      </div>
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        width="100%"
        height={VIEW_H}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Burn thermal map, ${present.length} channel${present.length === 1 ? "" : "s"}`}
      >
        {gridY.map((y) => (
          <line
            key={y}
            x1={0}
            y1={y}
            x2={VIEW_W}
            y2={y}
            stroke="var(--border-subtle)"
            strokeWidth={1}
            opacity={0.5}
          />
        ))}
        {present.map((c, i) => {
          const color = indigoTone(i);
          return segments(data.channels[c].points, gaps).map((seg, si) => (
            <polyline
              key={`${c}-${si}`}
              points={seg.map(([t, v]) => `${xScale(t)},${yScale(v, lo, hi)}`).join(" ")}
              fill="none"
              stroke={color}
              strokeWidth={2}
              data-channel={c}
            />
          ));
        })}
        {/* direct end-labels, no legend box */}
        {present.map((c, i) => {
          const pts = data.channels[c].points;
          const last = pts[pts.length - 1];
          return (
            <text
              key={`lbl-${c}`}
              x={Math.min(xScale(last[0]) + 4, VIEW_W - 20)}
              y={yScale(last[1], lo, hi)}
              fill={indigoTone(i)}
              fontSize="var(--fs-12)"
              className="mono"
            >
              {c}
            </text>
          );
        })}
      </svg>
      {gaps.length > 0 && (
        <div className={styles.gapNote}>
          {gaps.length} sensor gap{gaps.length === 1 ? "" : "s"} — shown as breaks,
          never interpolated
        </div>
      )}
    </div>
  );
}
