import CardError from "../../ui/CardError/CardError";
import Skeleton from "../../components/Skeleton/Skeleton";
import HorizontalBarList from "../../ui/HorizontalBarList/HorizontalBarList";
import { humanizeReason } from "../../config/blockerReasons";

/**
 * What's blocking issuance — a ranked, horizontal breakdown of the compliance
 * gates unmet across provisional batches. Reads the `reasons_histogram`
 * already returned by getSummary() (no new endpoint). Each row is an
 * actionable, fixable blocker, so it's a horizontal "bar-table" (humanized
 * reason · magnitude bar · exact count) rather than a vertical bar chart —
 * long reason names stay fully readable and the counts are visible without
 * hovering. An empty/null `reasons` object is a real "no blockers" reading,
 * rendered honestly by the list's own empty state, never a fabricated bar.
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
  // Humanize the raw reason codes for display; keep the raw code as a hover
  // hint so it stays copy-pasteable for logs/API. Sorting is handled by the
  // list itself (descending).
  const items = Object.entries(reasons ?? {}).map(([code, value]) => ({
    label: humanizeReason(code),
    value,
    hint: code,
  }));

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <span className="micro">What&apos;s blocking issuance</span>
      <div className="micro" style={{ marginTop: 2 }}>
        compliance gates unmet on provisional batches
      </div>
      <div style={{ marginTop: 12 }}>
        {loading && <Skeleton variant="card" />}
        {!loading && error && (
          <CardError message="Failed to load issuance blockers." onRetry={onRetry} />
        )}
        {!loading && !error && (
          <HorizontalBarList
            items={items}
            valueSuffix="batches"
            ariaLabel="Issuance blockers by compliance gate"
            emptyLabel="No blockers — all batches issuable"
          />
        )}
      </div>
    </div>
  );
}
