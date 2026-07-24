import { useCallback, useEffect, useState } from "react";
import { getCreditTimeseries, type CreditTimeseries } from "../api";
import KpiRow from "./Dashboard/KpiRow";

export default function Dashboard() {
  const [data, setData] = useState<CreditTimeseries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  // INV-6: the dashboard's numbers all come from this ONE metrics endpoint —
  // never also call getSummary here, since its counts answer a different
  // question and could silently diverge from this figure.
  const fetchTotals = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const d = await getCreditTimeseries({});
      setData(d);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    document.title = "Dashboard · TerraCipher";
  }, []);

  useEffect(() => {
    fetchTotals();
  }, [fetchTotals]);

  return (
    <div className="wrap">
      <h1 className="page-title">Dashboard</h1>
      <KpiRow
        totals={data?.totals ?? null}
        loading={loading}
        error={error}
        onRetry={fetchTotals}
      />
    </div>
  );
}
