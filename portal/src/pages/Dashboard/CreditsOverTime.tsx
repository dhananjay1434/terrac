import type { CreditBucket, CreditBucketGranularity } from "../../api";
import { fmtCredit } from "../../format";
import CardError from "../../ui/CardError/CardError";
import Skeleton from "../../components/Skeleton/Skeleton";
import BucketToggle from "../../ui/BucketToggle/BucketToggle";
import { GRANULARITY_OPTIONS } from "../../config/chartRange";
import DivergingStackedBarChart, {
  type DivergingBar,
} from "../../ui/DivergingStackedBarChart/DivergingStackedBarChart";
import { indigoTone } from "../../config/chartPalette";

// Period formatter: detects daily (YYYY-MM-DD) vs monthly (YYYY-MM) format.
// Daily: "May 15", Monthly: "Jan 2026". Pure display formatting, not timezone conversion.
function formatPeriod(period: string): string {
  const parts = period.split("-").map(Number);
  if (parts.length === 3) {
    // Daily: YYYY-MM-DD -> "May 15" format
    const [year, month, day] = parts;
    const d = new Date(Date.UTC(year, month - 1, day));
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
  }
  // Monthly: YYYY-MM -> "Jan 2026" format
  const [year, month] = parts;
  const d = new Date(Date.UTC(year, month - 1, 1));
  return d.toLocaleDateString(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
}

// Our real CSI methodology's terms — NEVER BlueLayer's labels ("E biomass" /
// "E production"), which we do not compute. See PHASE_1E blueprint: Net
// credit (above zero) vs. Safety margin / Transport / Pyrolysis (CH4)
// (stacked below zero) — deductions, not the removal itself. Colors are
// tones of our one brand hue (indigoTone — see config/chartPalette), never
// hardcoded inline.
function toDivergingBar(b: CreditBucket): DivergingBar {
  const c = b.components ?? {
    safety_t_co2e: 0,
    transport_t_co2e: 0,
    ch4_t_co2e: 0,
    gross_t_co2e: 0,
  };
  // Distinguish the two zero-credit period types the tooltip would otherwise
  // render identically: a period with provisional (pipeline) batches awaiting
  // corroboration vs. a genuinely empty period. Honest — never invents credit.
  let note: string | undefined;
  if (b.issued_count === 0) {
    note =
      b.provisional_count > 0
        ? `${b.provisional_count} provisional (pipeline) — not yet issued`
        : "No credits issued this period";
  }
  return {
    label: formatPeriod(b.period),
    note,
    above: [{ label: "Net credit", value: b.issued_credit_t_co2e, color: indigoTone(0) }],
    below: [
      { label: "Safety margin", value: c.safety_t_co2e, color: indigoTone(1) },
      { label: "Transport", value: c.transport_t_co2e, color: indigoTone(2) },
      { label: "Pyrolysis (CH₄)", value: c.ch4_t_co2e, color: indigoTone(3) },
    ],
    tooltip: [
      { label: "Net credit", value: b.issued_credit_t_co2e, bold: true },
      { label: "− Safety margin", value: c.safety_t_co2e },
      { label: "− Transport", value: c.transport_t_co2e },
      { label: "− Pyrolysis (CH₄)", value: c.ch4_t_co2e },
      { label: "Gross (informational)", value: c.gross_t_co2e },
    ],
  };
}

/**
 * Credits issued over time. Receives the already-fetched buckets from
 * Dashboard (INV-6 — one fetch of the metrics endpoint feeds both KpiRow and
 * this chart; fetching a second time here would be a redundant call to the
 * same data).
 */
export default function CreditsOverTime({
  buckets,
  loading,
  error,
  onRetry,
  bucket = "week",
  onBucket = () => {},
}: {
  buckets: CreditBucket[] | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
  bucket?: CreditBucketGranularity;
  onBucket?: (b: CreditBucketGranularity) => void;
}) {
  const caption =
    buckets && buckets.length > 0
      ? `${formatPeriod(buckets[0].period)} – ${formatPeriod(buckets[buckets.length - 1].period)}`
      : null;

  return (
    <div className="card" style={{ marginTop: "var(--space-4)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "var(--space-3)" }}>
        <div>
          <span className="micro">Credits issued and deductions over time</span>
          {caption && (
            <div className="micro" style={{ marginTop: "var(--space-1)" }}>
              {caption}
            </div>
          )}
        </div>
        <BucketToggle
          options={GRANULARITY_OPTIONS}
          selected={bucket}
          onSelect={onBucket}
          ariaLabel="Chart granularity"
        />
      </div>
      <div style={{ marginTop: "var(--space-3)" }}>
        {loading && <Skeleton variant="card" />}
        {!loading && error && (
          <CardError message="Failed to load credits over time." onRetry={onRetry} />
        )}
        {!loading && !error && (
          <DivergingStackedBarChart
            // Zero-value months (INV-5, a real absence-of-credit reading)
            // are already part of `buckets` from the backend's zero-fill —
            // passed straight through, never filtered.
            data={(buckets ?? []).map(toDivergingBar)}
            formatValue={fmtCredit}
            emptyLabel="No credits issued yet"
            ariaLabel="Credits issued and deductions over time"
          />
        )}
      </div>
    </div>
  );
}
