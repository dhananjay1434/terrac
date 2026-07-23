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
  const flat = hi === lo;

  if (readings.length === 1) {
    const y = flat ? 100 : 100;
    return (
      <svg viewBox="0 0 600 200" width="100%" height="200" role="img" aria-label="Burn temperature">
        <circle cx={300} cy={y} r={4} fill="var(--accent, currentColor)" />
        <text x="4" y="16" className="micro">{hi}°C</text>
      </svg>
    );
  }

  const n = readings.length;
  const points = readings
    .map((t, i) => {
      const x = (i / (n - 1)) * 600;
      const y = flat ? 100 : 200 - ((t - lo) / (hi - lo)) * 200;
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <svg viewBox="0 0 600 200" width="100%" height="200" role="img" aria-label="Burn temperature">
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent, currentColor)"
        strokeWidth={2}
      />
      <text x="4" y="16" className="micro">{hi}°C</text>
      <text x="4" y="196" className="micro">{lo}°C</text>
    </svg>
  );
}
