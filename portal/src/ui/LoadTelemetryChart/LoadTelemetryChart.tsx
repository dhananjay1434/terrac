import { indigoTone } from "@config/chartPalette";
import { fmtKg } from "../../format";
import ChartFrame from "../ChartFrame/ChartFrame";
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

export default function LoadTelemetryChart({ data }: { data: LoadTelemetryData }) {
  const pts = data.points ?? [];
  if (pts.length === 0) return null; // Tier-aware: no load cells → no chart

  const t0 = pts[0][0];
  const t1 = pts[pts.length - 1][0];
  const span = t1 - t0 || 1; // single-point / zero-span burn → avoid divide-by-zero
  const hi = Math.max(...pts.map((p) => p[1]), 1);

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

  const last = pts[pts.length - 1];

  return (
    <div className={styles.wrap}>
      <ChartFrame
        ariaLabel="Continuous kiln load weight"
        title="Load telemetry"
        yDomain={[0, hi]}
        headerStats={chips}
      >
        {({ w, yScale: yy }) => {
          const xScale = (t: number) => ((t - t0) / span) * w;
          return (
            <>
              <polyline
                points={stepPts.map(([t, v]) => `${xScale(t)},${yy(v)}`).join(" ")}
                fill="none"
                stroke={indigoTone(0)}
                strokeWidth={2}
              />
              {pts.map(([t, v], i) => (
                <circle
                  key={i}
                  cx={xScale(t)}
                  cy={yy(v)}
                  r={2.5}
                  fill={indigoTone(0)}
                >
                  <title>{fmtKg(v)}</title>
                </circle>
              ))}
              <circle
                cx={xScale(last[0])}
                cy={yy(last[1])}
                r={4}
                fill={indigoTone(0)}
                stroke="var(--surface-card)"
                strokeWidth={1.5}
              />
            </>
          );
        }}
      </ChartFrame>
    </div>
  );
}
