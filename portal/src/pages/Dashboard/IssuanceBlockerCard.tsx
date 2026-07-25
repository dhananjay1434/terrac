import Card from "../../ui/Card/Card";
import Button from "../../ui/Button/Button";
import Skeleton from "../../components/Skeleton/Skeleton";
import BarChart from "../../ui/BarChart/BarChart";

/**
 * What's blocking issuance — a ranked bar chart of compliance-gate reasons
 * across provisional batches. Reads the `reasons_histogram` already returned
 * by getSummary() (no new endpoint). An empty (or null) `reasons` object is
 * a real "no blockers" reading, not a missing-data gap — BarChart's own
 * empty-state renders that honestly instead of a fabricated bar.
 */
export default function IssuanceBlockerCard({
  reasons,
  loading,
  error,
  onRetry,
}: {
  reasons: Record<string, number> | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  // Sorted descending — the most common blocker first.
  const data = Object.entries(reasons ?? {})
    .sort((a, b) => b[1] - a[1])
    .map(([label, value]) => ({ label, value }));

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <span className="micro">What&apos;s blocking issuance</span>
      <div className="micro" style={{ marginTop: 2 }}>
        compliance gates unmet on provisional batches
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
              Failed to load issuance blockers.
            </span>
            <Button variant="neutral" size="sm" onClick={onRetry}>
              Retry
            </Button>
          </Card>
        )}
        {!loading && !error && (
          <BarChart
            data={data}
            ariaLabel="Issuance blockers"
            emptyLabel="No blockers — all batches issuable"
          />
        )}
      </div>
    </div>
  );
}
