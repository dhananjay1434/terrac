import type { QualityMetrics } from "../../api";
import Card from "../../ui/Card/Card";
import Button from "../../ui/Button/Button";
import StatBand from "../../ui/StatBand/StatBand";
import StatTile from "../../components/StatTile/StatTile";
import Skeleton from "../../components/Skeleton/Skeleton";
import BarChart from "../../ui/BarChart/BarChart";

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
          <Card
            style={{
              borderColor: "var(--status-error-fg)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <span className="err" style={{ margin: 0 }}>
              Failed to load permanence quality.
            </span>
            <Button variant="neutral" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </Card>
        )}
        {!loading && !error && data && data.n > 0 && (
          <>
            <StatBand>
              <StatTile
                label="Avg permanence"
                value={`${Math.round(data.permanence_pct!.avg)}%`}
              />
              <StatTile
                label="Avg H/Corg"
                value={data.h_corg!.avg.toFixed(2)}
                hint="lower = more durable"
              />
            </StatBand>
            <div style={{ marginTop: 12 }}>
              <BarChart
                data={data.distribution.map((d) => ({
                  label: d.label,
                  value: d.count,
                }))}
                ariaLabel="Permanence distribution"
                emptyLabel="No lab results yet"
              />
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
