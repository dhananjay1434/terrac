import { useCallback, useEffect, useState } from "react";
import {
  getCreditTimeseries,
  getQualityMetrics,
  getSummary,
  type CreditTimeseries,
  type CreditBucketGranularity,
  type QualityMetrics,
} from "../api";
import KpiRow from "./Dashboard/KpiRow";
import CreditsOverTime from "./Dashboard/CreditsOverTime";
import PyrolysisQualityCard from "./Dashboard/PyrolysisQualityCard";
import PermanenceQualityCard from "./Dashboard/PermanenceQualityCard";
import IssuanceBlockerCard from "./Dashboard/IssuanceBlockerCard";
import { windowFor } from "../config/chartRange";

export default function Dashboard() {
  const [data, setData] = useState<CreditTimeseries | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const [quality, setQuality] = useState<QualityMetrics | null>(null);
  const [qualityLoading, setQualityLoading] = useState(true);
  const [qualityError, setQualityError] = useState(false);

  const [reasons, setReasons] = useState<Record<string, number> | null>(null);
  const [provisionalCount, setProvisionalCount] = useState<number | null>(null);
  const [reasonsLoading, setReasonsLoading] = useState(true);
  const [reasonsError, setReasonsError] = useState(false);

  // Granularity drives BOTH the SQL bucket AND the time window (Stripe/Grafana
  // convention: finer granularity → shorter, denser, more-recent window). This
  // keeps bars contiguous at every level instead of scattering a handful of
  // daily spikes across a mostly-empty 6-month axis. Default "week" is the
  // sweet spot where artisanal batch cadence reads as a full, continuous
  // series. See config/chartRange for the window mapping.
  const [bucket, setBucket] = useState<CreditBucketGranularity>("week");

  // INV-6: the credit KPIs/chart come from ONE metrics endpoint — never also
  // call getSummary for that figure, since its counts answer a different
  // question and could silently diverge. The quality/blocker section below
  // is a SEPARATE, clearly-labeled analytics area (read-only, never
  // credit-affecting) with its own independent fetches.
  const fetchTotals = useCallback(async () => {
    setLoading(true);
    setError(false);
    try {
      const { from, to } = windowFor(bucket);
      const d = await getCreditTimeseries({
        from: from.toISOString(),
        to: to.toISOString(),
        bucket,
      });
      setData(d);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, [bucket]);

  const fetchQuality = useCallback(async () => {
    setQualityLoading(true);
    setQualityError(false);
    try {
      const q = await getQualityMetrics();
      setQuality(q);
    } catch {
      setQualityError(true);
    } finally {
      setQualityLoading(false);
    }
  }, []);

  const fetchReasons = useCallback(async () => {
    setReasonsLoading(true);
    setReasonsError(false);
    try {
      const s = await getSummary();
      setReasons(s.reasons_histogram);
      setProvisionalCount(s.provisional);
    } catch {
      setReasonsError(true);
    } finally {
      setReasonsLoading(false);
    }
  }, []);

  useEffect(() => {
    document.title = "Dashboard · TerraCipher";
  }, []);

  useEffect(() => {
    fetchTotals();
    fetchQuality();
    fetchReasons();
  }, [fetchTotals, fetchQuality, fetchReasons]);

  return (
    <div className="wrap">
      <h1 className="page-title">Dashboard</h1>
      <KpiRow
        totals={data?.totals ?? null}
        loading={loading}
        error={error}
        onRetry={fetchTotals}
      />
      <CreditsOverTime
        buckets={data?.buckets ?? null}
        loading={loading}
        error={error}
        onRetry={fetchTotals}
        bucket={bucket}
        onBucket={setBucket}
      />

      <h2 className="section-title" style={{ marginTop: "var(--space-6)" }}>
        Batch Quality & Operations
      </h2>
      <div className="micro" style={{ marginBottom: 12 }}>
        Read-only analytics — never affects issued credits.
      </div>
      <PyrolysisQualityCard
        data={quality?.pyrolysis ?? null}
        loading={qualityLoading}
        error={qualityError}
        onRetry={fetchQuality}
      />
      <div style={{ marginTop: 16 }}>
        <PermanenceQualityCard
          data={quality?.permanence ?? null}
          loading={qualityLoading}
          error={qualityError}
          onRetry={fetchQuality}
        />
      </div>
      <div style={{ marginTop: 16 }}>
        <IssuanceBlockerCard
          reasons={reasons}
          provisionalCount={provisionalCount}
          loading={reasonsLoading}
          error={reasonsError}
          onRetry={fetchReasons}
        />
      </div>
    </div>
  );
}
