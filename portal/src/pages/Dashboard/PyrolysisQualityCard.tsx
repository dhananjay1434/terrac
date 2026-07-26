import type { QualityMetrics } from "../../api";
import CardError from "../../ui/CardError/CardError";
import StatTile from "../../components/StatTile/StatTile";
import Skeleton from "../../components/Skeleton/Skeleton";
import styles from "./PyrolysisQualityCard.module.css";

/**
 * Read-only analytics — never credit-affecting. A batch missing telemetry is
 * excluded from these stats (never defaulted to a fabricated 0).
 */
export default function PyrolysisQualityCard({
  data,
  loading,
  error,
  onRetry,
}: {
  data: QualityMetrics["pyrolysis"] | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  return (
    <div className="card">
      <span className="micro">Pyrolysis quality</span>
      <div className="micro" style={{ marginTop: "var(--space-1)" }}>
        burn temperature drives char permanence
      </div>
      <div style={{ marginTop: "var(--space-3)" }}>
        {loading && <Skeleton variant="card" />}
        {!loading && error && (
          <CardError message="Failed to load pyrolysis quality." onRetry={onRetry} />
        )}
        {!loading && !error && data && data.n > 0 && (
          <>
            <div className={styles.statRow}>
              <StatTile
                label="Peak temp (°C)"
                value={String(Math.round(data.peak_temp_c!.avg))}
                hint={`avg across ${data.n} batches`}
              />
              <StatTile
                label={`Burn ≥ ${data.threshold_c}°C`}
                value={`${Math.round(data.pct_above_threshold!.avg)}%`}
                hint="of readings"
              />
            </div>
            {data.excluded > 0 && (
              <div className="micro" style={{ marginTop: "var(--space-2)" }}>
                {data.excluded} batches lack telemetry
              </div>
            )}
          </>
        )}
        {!loading && !error && (!data || data.n === 0) && (
          <div className="micro">Insufficient telemetry yet</div>
        )}
      </div>
    </div>
  );
}
