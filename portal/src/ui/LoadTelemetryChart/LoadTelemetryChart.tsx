import { indigoTone } from "@config/chartPalette";
import { fmtKg } from "../../format";
import styles from "./LoadTelemetryChart.module.css";

/**
 * Continuous load-cell weight curve (M2.8). Step-after path (weight is a series
 * of discrete additions, not a smooth signal), with a dot at each load event.
 * Chips summarise biomass in / biochar out / last load.
 *
 * Tier-aware (Global Rule 10): returns null when there is no LOAD channel — a
 * kiln without load cells simply doesn't render this; nothing breaks, nothing
 * nags. Weight then stays app/scale-evidenced via the existing flow.
 */
export interface LoadTelemetryData {
  points: [number, number][]; // [epoch_ms, gross_kg]
  biomass_kg?: number | null;
  biochar_kg?: number | null;
  last_load_kg?: number | null;
}

const VIEW_W = 600;
const VIEW_H = 160;
const Y_TOP = 8;
const Y_BOT = 148;

export default function LoadTelemetryChart({ data }: { data: LoadTelemetryData }) {
  const pts = data.points ?? [];
  if (pts.length === 0) return null; // Tier-aware: no load cells → no chart

  const t0 = pts[0][0];
  const t1 = pts[pts.length - 1][0];
  const span = t1 - t0 || 1; // single-point / zero-span burn → avoid divide-by-zero
  const hi = Math.max(...pts.map((p) => p[1]), 1);
  const xScale = (t: number) => ((t - t0) / span) * VIEW_W;
  const yScale = (v: number) => Y_BOT - (v / hi) * (Y_BOT - Y_TOP);

  // step-after: hold each value until the next sample
  const stepPts: [number, number][] = [];
  pts.forEach(([t, v], i) => {
    stepPts.push([t, v]);
    if (i < pts.length - 1) stepPts.push([pts[i + 1][0], v]);
  });

  const chips: { label: string; value: string }[] = [];
  if (data.biomass_kg != null) chips.push({ label: "Biomass", value: fmtKg(data.biomass_kg) });
  if (data.biochar_kg != null) chips.push({ label: "Biochar", value: fmtKg(data.biochar_kg) });
  if (data.last_load_kg != null) chips.push({ label: "Last load", value: fmtKg(data.last_load_kg) });

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <span className="micro">Load telemetry</span>
        <div className={styles.chips}>
          {chips.map((c) => (
            <span key={c.label} className={styles.chip}>
              <span className="micro">{c.label}</span>
              <span className="mono tabular">{c.value}</span>
            </span>
          ))}
        </div>
      </div>
      <svg
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        width="100%"
        height={VIEW_H}
        preserveAspectRatio="none"
        role="img"
        aria-label="Continuous kiln load weight"
      >
        <line
          x1={0}
          y1={Y_BOT}
          x2={VIEW_W}
          y2={Y_BOT}
          stroke="var(--border-subtle)"
          strokeWidth={1}
        />
        <polyline
          points={stepPts.map(([t, v]) => `${xScale(t)},${yScale(v)}`).join(" ")}
          fill="none"
          stroke={indigoTone(0)}
          strokeWidth={2}
        />
        {pts.map(([t, v], i) => (
          <circle
            key={i}
            cx={xScale(t)}
            cy={yScale(v)}
            r={2.5}
            fill={indigoTone(0)}
          >
            <title>{fmtKg(v)}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}
