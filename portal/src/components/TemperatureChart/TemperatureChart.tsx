import ChartFrame from "../../ui/ChartFrame/ChartFrame";

/**
 * Inline SVG burn-temperature curve — no charting dependency. Renders the raw
 * thermocouple readings as-is; never interpolates or fabricates points.
 */
export default function TemperatureChart({
  readings,
  minTemp,
  maxTemp,
}: {
  readings: number[];
  minTemp: number | null;
  maxTemp: number | null;
}) {
  if (!readings || readings.length === 0) {
    return (
      <div className="text-tertiary micro">
        No thermocouple telemetry for this batch.
      </div>
    );
  }

  const lo = minTemp ?? Math.min(...readings);
  const hi = maxTemp ?? Math.max(...readings);
  const mid = Math.round((hi + lo) / 2);
  const yFormat = (v: number) => `${Math.round(v)}°C`;

  if (readings.length === 1) {
    return (
      <ChartFrame
        ariaLabel="Burn temperature"
        yDomain={[lo, hi]}
        yTicks={[hi]}
        yFormat={yFormat}
      >
        {({ w, yScale: yy }) => (
          <circle cx={w / 2} cy={yy(hi)} r={4} fill="var(--indigo-600)" />
        )}
      </ChartFrame>
    );
  }

  const n = readings.length;

  return (
    <ChartFrame
      ariaLabel="Burn temperature"
      yDomain={[lo, hi]}
      yTicks={Array.from(new Set([hi, mid, lo]))}
      yFormat={yFormat}
    >
      {({ w, yScale: yy }) => {
        const coords = readings.map((t, i) => ({
          x: (i / (n - 1)) * w,
          y: yy(t),
          t,
        }));
        const points = coords.map(({ x, y }) => `${x},${y}`).join(" ");
        return (
          <>
            <polyline
              points={points}
              fill="none"
              stroke="var(--indigo-600)"
              strokeWidth={2}
            />
            {coords.map(({ x, y, t }, i) => (
              <circle key={i} cx={x} cy={y} r={2.5} fill="var(--indigo-600)">
                <title>{t}°C</title>
              </circle>
            ))}
          </>
        );
      }}
    </ChartFrame>
  );
}
