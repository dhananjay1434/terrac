import type { QualityMetrics } from "../../api";
import CardError from "../../ui/CardError/CardError";
import StatTile from "../../components/StatTile/StatTile";
import Skeleton from "../../components/Skeleton/Skeleton";
import HorizontalBarList from "../../ui/HorizontalBarList/HorizontalBarList";
import styles from "./PermanenceQualityCard.module.css";

// The CSI 100-year decay model yields one of two permanence outcomes: the
// top stability tier (H:Corg < 0.4 → ~83% retention) or the lower tier
// (H:Corg ≥ 0.4 → 70%). It is a two-outcome QUALITY split, not a continuous
// spread — so we show the durability-tier breakdown (which reads as a clear
// story) rather than a 4-bucket histogram that is structurally mostly empty.
// The "80%+" distribution bucket is exactly the top tier; everything below
// it is the lower tier.
const TOP_TIER_BUCKET = "80%+";

/**
 * Read-only analytics — never credit-affecting. A batch missing a lab H/Corg
 * reading is excluded from these stats (never defaulted to a fabricated 0%).
 */
export default function PermanenceQualityCard({
  data,
  loading,
  error,
  onRetry,
}: {
  data: QualityMetrics["permanence"] | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  return (
    <div className="card">
      <span className="micro">Permanence quality</span>
      <div className="micro" style={{ marginTop: 2 }}>
        H/Corg ratio → 100-year carbon durability
      </div>
      <div style={{ marginTop: 12 }}>
        {loading && <Skeleton variant="card" />}
        {!loading && error && (
          <CardError message="Failed to load permanence quality." onRetry={onRetry} />
        )}
        {!loading && !error && data && data.n > 0 && (
          <>
            <div className={styles.statRow}>
              <StatTile
                label="Avg permanence"
                value={`${Math.round(data.permanence_pct!.avg)}%`}
              />
              <StatTile
                label="Avg H/Corg"
                value={data.h_corg!.avg.toFixed(2)}
                hint="lower = more durable"
              />
            </div>
            <div style={{ marginTop: 16 }}>
              {(() => {
                const topTier =
                  data.distribution.find((d) => d.label === TOP_TIER_BUCKET)?.count ?? 0;
                const lowerTier = data.n - topTier;
                return (
                  <HorizontalBarList
                    items={[
                      {
                        label: "Top-tier durable (~83%)",
                        value: topTier,
                        hint: "H:Corg < 0.4 · ~83% retained at 100 yr",
                      },
                      {
                        label: "Lower-tier (~70%)",
                        value: lowerTier,
                        hint: "H:Corg ≥ 0.4 · 70% retained at 100 yr",
                      },
                    ]}
                    valueSuffix="batches"
                    ariaLabel="Permanence by durability tier"
                  />
                );
              })()}
            </div>
            {data.excluded > 0 && (
              <div className="micro" style={{ marginTop: 8 }}>
                {data.excluded} batches lack a lab H/Corg
              </div>
            )}
          </>
        )}
        {!loading && !error && (!data || data.n === 0) && (
          <div className="micro">No lab permanence data yet</div>
        )}
      </div>
    </div>
  );
}
