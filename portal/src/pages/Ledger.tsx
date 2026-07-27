import { useEffect, useState } from "react";
import { getBiomassLedger, type BiomassLedgerResponse } from "../api2";
import StatTile from "../components/StatTile/StatTile";
import BarChart from "../ui/BarChart/BarChart";
import HorizontalBarList from "../ui/HorizontalBarList/HorizontalBarList";
import BucketToggle from "../ui/BucketToggle/BucketToggle";
import styles from "./Ledger.module.css";
import ErrorBoundary from "../ui/ErrorBoundary/ErrorBoundary";
import CardError from "../ui/CardError/CardError";

function LedgerContent() {
  const [bucket, setBucket] = useState<"day" | "month">("month");
  
  const [data, setData] = useState<BiomassLedgerResponse | null>(null);
  const [error, setError] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    let canceled = false;
    setLoading(true);
    setError(false);
    getBiomassLedger({ bucket })
      .then((res) => {
        if (!canceled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch(() => {
        if (!canceled) {
          setError(true);
          setLoading(false);
        }
      });
    return () => {
      canceled = true;
    };
  }, [bucket]);

  if (error) return <CardError message="Failed to load ledger data." onRetry={() => setBucket(bucket)} />;
  if (loading || !data) return <div className={styles.loading}>Loading ledger...</div>;

  const chartData = data.buckets.map((b) => ({
    label: b.period,
    value: b.total_kg,
  }));

  const speciesData = Object.entries(data.totals.by_species).map(([species, kg]) => ({
    label: species.replace(/_/g, " "),
    value: kg,
  })).sort((a, b) => b.value - a.value);

  return (
    <div className={styles.grid}>
      <div className={styles.totalsCard}>
        <div style={{ display: "flex", gap: "1rem" }}>
          <StatTile
            label="Total Biomass (kg)"
            value={data.totals.total_kg.toLocaleString()}
          />
          <StatTile
            label="Batches"
            value={data.totals.row_count.toLocaleString()}
          />
        </div>
      </div>
      
      <div className={`card ${styles.chartCard}`}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
          <span className="micro">Biomass Over Time</span>
          <BucketToggle 
            options={[
              { label: "Daily", value: "day" },
              { label: "Monthly", value: "month" }
            ]}
            selected={bucket} 
            onSelect={(v) => setBucket(v as "day" | "month")} 
          />
        </div>
        <div className={styles.chartWrap}>
          <BarChart data={chartData} formatValue={(v) => `${v.toLocaleString()} kg`} />
        </div>
      </div>

      <div className={`card ${styles.speciesCard}`}>
        <span className="micro" style={{ display: "block", marginBottom: "1rem" }}>Feedstock Species</span>
        <HorizontalBarList items={speciesData} formatValue={(v) => `${v.toLocaleString()} kg`} />
      </div>
      
      <div className={`card ${styles.tableCard}`}>
        <span className="micro" style={{ display: "block", marginBottom: "1rem" }}>Raw Ledger Data</span>
        <div className={styles.tableWrap}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Period</th>
                <th className={styles.num}>Batches</th>
                <th className={styles.num}>Biomass (kg)</th>
                <th>Dominant Species</th>
              </tr>
            </thead>
            <tbody>
              {data.buckets.map((b) => {
                let domSpecies = "N/A";
                let maxKg = -1;
                for (const [s, kg] of Object.entries(b.by_species)) {
                  if (kg > maxKg) {
                    maxKg = kg;
                    domSpecies = s;
                  }
                }

                return (
                  <tr key={b.period}>
                    <td>{b.period}</td>
                    <td className={styles.num}>{b.row_count}</td>
                    <td className={styles.num}>{b.total_kg.toLocaleString()}</td>
                    <td>{domSpecies.replace(/_/g, " ")}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function Ledger() {
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>Biomass Ledgers</h1>
        <p className={styles.subtitle}>
          Aggregated biomass intake for all networks.
        </p>
      </header>
      <ErrorBoundary>
        <LedgerContent />
      </ErrorBoundary>
    </div>
  );
}
