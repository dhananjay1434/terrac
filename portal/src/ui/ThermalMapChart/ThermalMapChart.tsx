import { categoricalTone } from "@config/chartPalette";
import ChartFrame from "../ChartFrame/ChartFrame";
import ChartTooltip from "../ChartTooltip/ChartTooltip";
import { useHoverSync } from "../HoverSync/HoverSync";
import { sampleAt, elapsed } from "../../lib/telemetry/lookup";
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

const CHANNEL_ORDER = ["T1", "T2", "T3", "T4"] as const;
// Placement of each probe (matches the edge DemoProfile.probes) — shown in the
// end-label so four live lines are self-describing (T4·bottom, T1·side…).
const PLACEMENT: Record<string, string> = { T1: "side", T2: "side", T3: "side", T4: "bottom" };

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
  height,
}: {
  data: ThermalMapData;
  /** Whether the sustained-temperature compliance gate has passed. Colors the
   * MAX badge — the compliance tie-in a plain chart lacks. Computed by the
   * caller (backend/credit engine), never by this presentational component. */
  gateSatisfied?: boolean;
  /** Pass-through to ChartFrame's `height` (default 200) — lets a compact card
   * render short and an expanded modal render tall from the SAME component. */
  height?: number;
}) {
  const present = CHANNEL_ORDER.filter((c) => data.channels[c]?.points.length);
  if (present.length === 0) return null; // Tier-aware: nothing to draw

  const allValues = present.flatMap((c) => data.channels[c].points.map((p) => p[1]));
  const lo = Math.min(...allValues);
  const hi = Math.max(...allValues);
  const peak = Math.max(...present.map((c) => data.channels[c].max));

  const t0 = data.burn.t_start;
  const span = (data.burn.t_end || t0) - t0 || 1; // guard zero-span burns
  const gaps = data.burn.gaps ?? [];

  const { hoverT, setHoverT } = useHoverSync();
  const rawFrac = hoverT == null ? null : (hoverT - t0) / span;
  const clampedFrac = rawFrac != null && rawFrac >= 0 && rawFrac <= 1 ? rawFrac : null;

  return (
    <div className={styles.wrap}>
      <ChartFrame
        ariaLabel={`Burn thermal map, ${present.length} channel${present.length === 1 ? "" : "s"}`}
        summary={`${present.join(", ")}. Peak temperature ${peak.toFixed(1)}°C.`}
        title="Real-time thermal mapping"
        yDomain={[lo, hi]}
        yFormat={(v) => v.toFixed(0)}
        height={height}
        legend={present.map((c, i) => ({ label: `${c}·${PLACEMENT[c] ?? ""}`, color: categoricalTone(i) }))}
        badge={
          <span className={styles.maxBadge} data-gate={gateSatisfied ? "pass" : "pending"}>
            MAX <span className="mono tabular">{peak.toFixed(1)}</span>°C
          </span>
        }
        onHoverFrac={(f) => setHoverT(f == null ? null : t0 + f * span)}
        crosshairFrac={clampedFrac}
      >
        {({ w, yScale: yy }) => {
          const xScale = (t: number) => ((t - t0) / span) * w;
          return (
            <>
              {present.map((c, i) => {
                const color = categoricalTone(i);
                return segments(data.channels[c].points, gaps).map((seg, si) => (
                  <polyline
                    key={`${c}-${si}`}
                    points={seg.map(([t, v]) => `${xScale(t)},${yy(v)}`).join(" ")}
                    fill="none"
                    stroke={color}
                    strokeWidth={2}
                    data-channel={c}
                  />
                ));
              })}
            </>
          );
        }}
      </ChartFrame>
      {clampedFrac != null && hoverT != null && (() => {
        const items = present
          .map((c, i) => {
            const v = sampleAt(data.channels[c].points, hoverT);
            return v == null
              ? null
              : { label: `${c}·${PLACEMENT[c] ?? ""}`, color: categoricalTone(i), value: `${v.toFixed(1)}°C` };
          })
          .filter((x): x is { label: string; color: string; value: string } => x != null);
        return items.length ? (
          <ChartTooltip label={elapsed(t0, hoverT)} items={items} xFrac={clampedFrac} />
        ) : null;
      })()}
      {gaps.length > 0 && (
        <div className={styles.gapNote}>
          {gaps.length} sensor gap{gaps.length === 1 ? "" : "s"} — shown as breaks,
          never interpolated
        </div>
      )}
    </div>
  );
}
