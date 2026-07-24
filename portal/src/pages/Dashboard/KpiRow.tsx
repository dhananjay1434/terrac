import type { CreditTimeseries } from "../../api";
import { fmtCredit } from "../../format";
import Card from "../../ui/Card/Card";
import Button from "../../ui/Button/Button";
import StatBand from "../../ui/StatBand/StatBand";
import StatTile from "../../components/StatTile/StatTile";
import Skeleton from "../../components/Skeleton/Skeleton";

/**
 * Headline credit KPIs. Reads ONLY the credit-timeseries totals (INV-6 —
 * single source of truth for the dashboard's numbers; never mixes in
 * getSummary's counts, which cover a different question).
 */
export default function KpiRow({
  totals,
  loading,
  error,
  onRetry,
}: {
  totals: CreditTimeseries["totals"] | null;
  loading: boolean;
  error: boolean;
  onRetry: () => void;
}) {
  if (loading) {
    return (
      <StatBand>
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </StatBand>
    );
  }

  if (error) {
    return (
      <Card
        style={{
          borderColor: "var(--status-error-fg)",
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <span className="err" style={{ margin: 0 }}>
          Failed to load credit totals.
        </span>
        <Button variant="neutral" size="sm" onClick={onRetry}>
          Retry
        </Button>
      </Card>
    );
  }

  if (!totals) return null;

  // INV-3: "issued" excludes provisional entirely — never render a fake 0
  // when there simply isn't any issued credit yet.
  const noIssuedYet = totals.issued_credit_t_co2e === 0 && totals.issued_count === 0;

  return (
    <StatBand>
      <StatTile
        label="Credits issued (tCO₂e)"
        value={noIssuedYet ? "—" : fmtCredit(totals.issued_credit_t_co2e)}
        hint={noIssuedYet ? "No credits issued yet" : undefined}
      />
      <StatTile label="Issued batches" value={String(totals.issued_count)} />
      <StatTile
        label="Provisional (pipeline)"
        value={String(totals.provisional_count)}
        hint="not yet issued"
      />
      <StatTile
        label="Provisional credit (tCO₂e)"
        value={fmtCredit(totals.provisional_credit_t_co2e)}
      />
    </StatBand>
  );
}
