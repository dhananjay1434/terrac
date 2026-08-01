import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBiomassLedger, type BiomassLedgerResponse } from "../api2";
import StatTile from "../components/StatTile/StatTile";
import StatusPill from "../ui/StatusPill/StatusPill";
import BarChart from "../ui/BarChart/BarChart";
import HorizontalBarList from "../ui/HorizontalBarList/HorizontalBarList";
import BucketToggle from "../ui/BucketToggle/BucketToggle";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import Skeleton from "../components/Skeleton/Skeleton";
import styles from "./Ledger.module.css";
import ErrorBoundary from "../ui/ErrorBoundary/ErrorBoundary";
import CardError from "../ui/CardError/CardError";

type LedgerBucketRow = BiomassLedgerResponse["buckets"][number];

/* ── Date preset helpers ─────────────────────────────────────────────────── */
type Preset = "mtd" | "ytd" | "custom";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}
function monthStart(): string {
  const d = new Date();
  return isoDate(new Date(d.getFullYear(), d.getMonth(), 1));
}
function yearStart(): string {
  return isoDate(new Date(new Date().getFullYear(), 0, 1));
}
function today(): string {
  return isoDate(new Date());
}

function LedgerContent() {
  const [bucket, setBucket] = useState<"day" | "month">("month");
  const [preset, setPreset] = useState<Preset>("ytd");
  const [from, setFrom] = useState(yearStart());
  const [to, setTo] = useState(today());

  const [data, setData] = useState<BiomassLedgerResponse | null>(null);
  const [error, setError] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  function applyPreset(p: Preset) {
    setPreset(p);
    if (p === "mtd") {
      setFrom(monthStart());
      setTo(today());
    } else if (p === "ytd") {
      setFrom(yearStart());
      setTo(today());
    }
    // "custom" — keep current from/to, user will edit
  }

  useEffect(() => {
    let canceled = false;
    setLoading(true);
    setError(false);
    getBiomassLedger({ bucket, from, to })
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
  }, [bucket, from, to]);

  if (error) return <CardError message="Failed to load ledger data." onRetry={() => setBucket(bucket)} />;
  if (loading || !data) {
    return (
      <div className={styles.grid}>
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

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
      {/* ── Date presets + bucket toggle ────────────────────────────── */}
      <div className={styles.controlsCard}>
        <div className={styles.presets}>
          {(["mtd", "ytd", "custom"] as const).map((p) => (
            <button
              key={p}
              type="button"
              className={styles.presetBtn}
              data-active={preset === p ? "true" : undefined}
              onClick={() => applyPreset(p)}
            >
              {p === "mtd" ? "MTD" : p === "ytd" ? "YTD" : "Custom"}
            </button>
          ))}
          {preset === "custom" && (
            <span className={styles.dateRange}>
              <input
                type="date"
                className={styles.dateInput}
                aria-label="From date"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
              />
              <span className="text-tertiary">→</span>
              <input
                type="date"
                className={styles.dateInput}
                aria-label="To date"
                value={to}
                onChange={(e) => setTo(e.target.value)}
              />
            </span>
          )}
        </div>
        <BucketToggle
          options={[
            { label: "Daily", value: "day" },
            { label: "Monthly", value: "month" },
          ]}
          selected={bucket}
          onSelect={(v) => setBucket(v as "day" | "month")}
        />
      </div>

      {/* ── Stat tiles ─────────────────────────────────────────────── */}
      <div className={styles.totalsCard}>
        <div className={styles.statRow}>
          <StatTile
            label="Total biomass"
            value={`${data.totals.total_kg.toLocaleString()} kg`}
          />
          <StatTile
            label="Batches"
            value={data.totals.row_count.toLocaleString()}
          />
        </div>
      </div>

      {/* ── Chart ──────────────────────────────────────────────────── */}
      <div className={`card ${styles.chartCard}`}>
        <div className={styles.chartHead}>
          <span className="micro">Biomass over time</span>
        </div>
        <div className={styles.chartWrap}>
          <BarChart data={chartData} height={160} formatValue={(v) => `${v.toLocaleString()} kg`} />
        </div>
      </div>

      {/* ── Species breakdown ──────────────────────────────────────── */}
      <div className={`card ${styles.speciesCard}`}>
        <span className="micro" style={{ display: "block", marginBottom: "var(--space-3)" }}>Feedstock species</span>
        <HorizontalBarList items={speciesData} formatValue={(v) => `${v.toLocaleString()} kg`} />
      </div>

      {/* ── Data table with species pills + batch_code links ───────── */}
      <div className={`card ${styles.tableCard}`}>
        <span className="micro" style={{ display: "block", marginBottom: "var(--space-3)" }}>Ledger detail</span>
        <DataTable<LedgerBucketRow>
          columns={ledgerColumns}
          rows={data.buckets}
          rowKey={(b) => b.period}
        />
      </div>
    </div>
  );
}

const ledgerColumns: ColumnDef<LedgerBucketRow>[] = [
  { key: "period", header: "Period", mono: true, render: (b) => b.period },
  {
    key: "batches",
    header: "Batches",
    align: "right",
    mono: true,
    render: (b) => b.row_count,
  },
  {
    key: "biomass",
    header: "Biomass (kg)",
    align: "right",
    mono: true,
    render: (b) => b.total_kg.toLocaleString(),
  },
  {
    key: "species",
    header: "Species",
    render: (b) => {
      const speciesEntries = Object.entries(b.by_species).sort(([, a], [, c]) => c - a);
      return (
        <span className={styles.pillRow}>
          {speciesEntries.length > 0
            ? speciesEntries.map(([s]) => (
                <StatusPill key={s} status="inert">
                  {s.replace(/_/g, " ")}
                </StatusPill>
              ))
            : "—"}
        </span>
      );
    },
  },
  {
    key: "codes",
    header: "Batch codes",
    render: (b) => (
      <span className={styles.codeRow}>
        {(b.batch_codes ?? []).length > 0
          ? b.batch_codes.map((code) => (
              <Link key={code} to={`/batches/${code}`} className={styles.codeChip}>
                {code}
              </Link>
            ))
          : "—"}
      </span>
    ),
  },
];

export default function Ledger() {
  return (
    <div className={`wrap ${styles.container}`}>
      <header className={styles.header}>
        <h1>Biomass ledgers</h1>
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
