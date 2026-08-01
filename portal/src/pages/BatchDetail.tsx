import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getBatch,
  getBatchTimeline,
  issueCredit,
  downloadExport,
  AuthError,
  ApiError,
  type BatchDetail as Detail,
  type MediaItem,
  type TimelineStage,
} from "../api";
import { getRole } from "../auth";
import { getBatchCapabilities } from "../api2";
import type { BatchCapabilities } from "../apiV2types";
import ComplianceChecklist from "../components/ComplianceChecklist/ComplianceChecklist";
import EvidenceLightbox from "../components/EvidenceLightbox/EvidenceLightbox";
import EvidenceGallery from "../components/EvidenceGallery/EvidenceGallery";
import StageTimeline from "../components/StageTimeline/StageTimeline";
import ConfirmModal from "../components/ConfirmModal/ConfirmModal";
import VerificationChain from "../components/VerificationChain/VerificationChain";
import MetricBlock from "../components/MetricBlock/MetricBlock";
import SealedVerdict from "../components/SealedVerdict/SealedVerdict";
import CopyButton from "../components/CopyButton/CopyButton";
import ProvenanceTile from "../components/ProvenanceTile/ProvenanceTile";
import LcaBreakdown from "../components/LcaBreakdown/LcaBreakdown";
import LcaFormula from "../components/LcaFormula/LcaFormula";
import BurnTelemetryChart from "../components/BurnTelemetryChart/BurnTelemetryChart";
import StatTile from "../components/StatTile/StatTile";
import Skeleton from "../components/Skeleton/Skeleton";
import { fmtCredit, fmtDate, fmtKg, fmtDateTime } from "../format";
import Button from "../ui/Button/Button";
import Card from "../ui/Card/Card";

const TIMELINE_V2 = true; // M3.3 feature flag

export const STEP_ORDER = [
  "batch_photo", "flame_curtain", "quenching", "flame_height",
  "smoke_0", "0", "smoke_50", "50", "smoke_90", "90", "smoke_100", "100",
  "post_burn_mass", "packaging", "end_use", "lab_certificate",
];

export const STEP_TITLES: Record<string, string> = {
  batch_photo: "Batch photo",
  flame_curtain: "Burn — flame curtain",
  quenching: "Burn — quenching",
  flame_height: "Burn — flame height",
  smoke_0: "Smoke opacity — 0%", "0": "Smoke opacity — 0%",
  smoke_50: "Smoke opacity — 50%", "50": "Smoke opacity — 50%",
  smoke_90: "Smoke opacity — 90%", "90": "Smoke opacity — 90%",
  smoke_100: "Smoke opacity — 100%", "100": "Smoke opacity — 100%",
  post_burn_mass: "Post-burn mass",
  packaging: "Packaging",
  end_use: "End use — field application",
  lab_certificate: "Lab certificate",
  other: "Other / Uncategorized"
};

export function groupMedia(items: MediaItem[]): [string, MediaItem[]][] {
  const groups = new Map<string, MediaItem[]>();
  for (const m of items) {
    const k = m.capture_type ?? "__unclassified__";
    (groups.get(k) ?? groups.set(k, []).get(k)!).push(m);
  }
  const keys = [...groups.keys()].sort((a, b) => {
    const ia = STEP_ORDER.indexOf(a), ib = STEP_ORDER.indexOf(b);
    if (a === "__unclassified__") return 1;
    if (b === "__unclassified__") return -1;
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
  return keys.map((k) => [k, groups.get(k)!]);
}

export default function BatchDetail() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState<Detail | null>(null);
  const [timeline, setTimeline] = useState<TimelineStage[]>([]);
  const [timelineLightbox, setTimelineLightbox] = useState<MediaItem | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);
  const [exporting, setExporting] = useState<"csi" | "rainbow" | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);

  function reload() {
    setErr(null);
    getBatch(uuid)
      .then(setD)
      .catch((e) => {
        if (e instanceof AuthError) nav("/login");
        else if (e instanceof ApiError && e.status === 404)
          setErr("Batch not found.");
        else setErr("Couldn't load batch.");
      });
    
    if (TIMELINE_V2) {
      getBatchTimeline(uuid)
        .then(setTimeline)
        .catch((e) => {
          // If legacy batch (404 timeline), no crash, just gallery
          if (e instanceof ApiError && e.status === 404) return;
          console.error("Failed to load timeline", e);
        });
    }
  }
  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [uuid]);

  useEffect(() => {
    if (d) document.title = `Batch ${uuid.slice(0, 8)} · TerraCipher`;
  }, [d, uuid]);

  async function issue() {
    if (!d) return;
    setIssuing(true);
    try {
      await issueCredit(uuid);
      setConfirmOpen(false);
      reload();
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Issue failed — the server re-checks eligibility.");
    } finally {
      setIssuing(false);
    }
  }

  async function exportAs(fmt: "csi" | "rainbow") {
    if (!d) return;
    setExporting(fmt);
    try {
      await downloadExport(uuid, fmt);
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Export failed — the batch must be issuable to export.");
    } finally {
      setExporting(null);
    }
  }

  if (err) {
    return (
      <div className="wrap err" style={{ textAlign: "center", paddingTop: "var(--space-8)" }}>
        <div className="text-primary" style={{ fontSize: 18, fontWeight: 600, marginBottom: "var(--space-4)" }}>{err}</div>
        <div
          style={{
            display: "flex",
            gap: "var(--space-3)",
            justifyContent: "center",
            alignItems: "center",
          }}
        >
          <Link to="/batches" className="link-indigo">← All batches</Link>
          <Button variant="neutral" size="sm" onClick={reload}>
            Retry
          </Button>
        </div>
      </div>
    );
  }
  if (!d) {
    return (
      <div
        className="wrap"
        style={{ display: "flex", flexDirection: "column", gap: "var(--space-4)" }}
      >
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
        <Skeleton variant="card" />
      </div>
    );
  }

  const okCount = d.compliance.checklist.filter((c) => c.ok).length;
  const total = d.compliance.checklist.length;
  const issued = d.batch.status === "ISSUED";
  const chainNodes = [
    {
      label: "Received",
      sublabel: d.batch.received_at ? fmtDate(d.batch.received_at) : undefined,
      state: d.batch.received_at ? ("done" as const) : ("pending" as const),
    },
    {
      label: "Evidence",
      sublabel: `${d.media.length} item${d.media.length === 1 ? "" : "s"}`,
      state: d.media.length > 0 ? ("done" as const) : ("pending" as const),
    },
    {
      label: "Compliance",
      sublabel: `${okCount}/${total} criteria`,
      state: d.compliance.issuable ? ("done" as const) : ("current" as const),
    },
    {
      label: "Issued",
      state: issued ? ("done" as const) : ("pending" as const),
    },
  ];

  return (
    <div className="wrap">
      <header className="print-only" aria-hidden>
        <div className="mono">{d.batch.batch_uuid}</div>
        <div>
          {d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"} · net credit{" "}
          {fmtCredit(d.batch.net_credit_t_co2e)} tCO₂e · printed {fmtDateTime(new Date().toISOString())}
        </div>
      </header>
      <VerificationChain nodes={chainNodes} />
      <div className="hero">
        <div className="hero-verdict">
          <SealedVerdict
            size="lg"
            verdict={issued ? "ISSUED" : d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"}
            reasonCount={d.compliance.reasons.length}
          />
          <div className="credit-label">
            Batch <span className="mono">{d.batch.batch_uuid.slice(0, 8)}</span>{" "}
            <CopyButton value={d.batch.batch_uuid} label="Copy batch id" /> ·
            device {d.batch.device_id ?? "—"}
          </div>
          {d.media.length > 0 && (
            <a
              className="link-indigo"
              style={{ fontSize: "var(--fs-13)" }}
              href="#evidence-media"
            >
              Review evidence ↓
            </a>
          )}
          {!issued && getRole() === "admin" && (
            <Button
              style={{ marginTop: "var(--space-4)" }}
              disabled={!d.compliance.issuable || issuing}
              onClick={() => setConfirmOpen(true)}
            >
              {issuing
                ? "Issuing…"
                : d.compliance.issuable
                  ? "Issue credit"
                  : "Not yet issuable"}
            </Button>
          )}
          {getRole() === "admin" && d.compliance.issuable && (
            <div
              className="export-row"
              style={{ marginTop: "var(--space-3)", display: "flex", gap: "var(--space-2)" }}
            >
              <Button
                variant="neutral"
                size="sm"
                disabled={exporting !== null}
                onClick={() => exportAs("csi")}
              >
                {exporting === "csi" ? "Exporting…" : "Export CSI"}
              </Button>
              <Button
                variant="neutral"
                size="sm"
                disabled={exporting !== null}
                onClick={() => exportAs("rainbow")}
              >
                {exporting === "rainbow" ? "Exporting…" : "Export Rainbow"}
              </Button>
            </div>
          )}
        </div>
        <div className="hero-figure">
          <MetricBlock
            value={fmtCredit(d.batch.net_credit_t_co2e)}
            unit="tCO₂e"
            caption="net credit"
          />
          <dl className="hero-facts">
            <div className="hero-fact">
              <dt className="micro">Wet yield</dt>
              <dd className="tabular">{fmtKg(d.batch.wet_yield_kg)}</dd>
            </div>
            <div className="hero-fact">
              <dt className="micro">Project</dt>
              <dd>{d.batch.project_id ?? "—"}</dd>
            </div>
            <div className="hero-fact">
              <dt className="micro">Received</dt>
              <dd className="tabular">
                {fmtDate(d.batch.received_at)}
              </dd>
            </div>
          </dl>
        </div>
      </div>

      <div className="tiles">
        <LcaBreakdown
          wetYieldKg={d.batch.wet_yield_kg}
          netCreditTCo2e={d.batch.net_credit_t_co2e}
        />
        <LcaFormula breakdown={d.lca_breakdown} />
        <ProvenanceTile
          batchUuid={d.batch.batch_uuid}
          deviceId={d.batch.device_id}
          projectId={d.batch.project_id}
          receivedAt={d.batch.received_at}
        />
      </div>

      <ComplianceChecklist checklist={d.compliance.checklist} />

      <Card as="section" style={{ marginTop: "var(--space-4)" }}>
        <span className="micro">Burn telemetry</span>
        <BurnTelemetryChart
          uuid={d.batch.batch_uuid}
          legacyReadings={d.telemetry?.temperature_readings ?? []}
          legacyMin={d.telemetry?.min_temp ?? null}
          legacyMax={d.telemetry?.max_temp ?? null}
          gateSatisfied={d.compliance.checklist.some((c) => c.code === "C3" && c.ok)}
          live={d.batch.status !== "ISSUED"}
        />
        <div className="tiles" style={{ marginTop: "var(--space-3)" }}>
          <StatTile label="Min temp" value={d.telemetry?.min_temp != null ? `${d.telemetry.min_temp}°C` : "—"} />
          <StatTile label="Max temp" value={d.telemetry?.max_temp != null ? `${d.telemetry.max_temp}°C` : "—"} />
          {/* Weight is a single post-burn measurement, not a time series —
              shown as a stat, not a curve. A weight-vs-time curve would
              require app-side series capture (out of scope). */}
          <StatTile label="Post-burn yield" value={fmtKg(d.batch.wet_yield_kg)} />
        </div>
      </Card>

      {TIMELINE_V2 && timeline.length > 0 && (
        <section className="card" style={{ marginTop: "var(--space-4)", overflow: "hidden" }}>
          <div className="micro" style={{ marginBottom: "var(--space-3)", padding: "var(--space-3) var(--space-4) 0" }}>Custody timeline</div>
          <div style={{ padding: "0 var(--space-4) var(--space-4)" }}>
            <StageTimeline
              stages={timeline}
              locked={d.batch.status === "ISSUED"}
              onOpenMedia={setTimelineLightbox}
              onVerified={() => {
                // Not ideal but functional: reload entirely to sync verdict across UI.
                // For a true SPA feel, we'd uplift overrides to BatchDetail.
                reload();
              }}
            />
          </div>
        </section>
      )}
      
      {timelineLightbox && (() => {
        const flat = timeline.flatMap((s) => s.media ?? []);
        const idx = flat.findIndex((m) => m.operation_id === timelineLightbox.operation_id);
        return (
          <EvidenceLightbox
            items={flat}
            index={idx >= 0 ? idx : 0}
            onClose={() => setTimelineLightbox(null)}
            onNavigate={(i) => setTimelineLightbox(flat[i])}
          />
        );
      })()}

      <EvidenceGallery media={d.media} locked={d.batch.status === "ISSUED"} />

      <ConfirmModal
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Issue credit — permanent"
        previewRows={[
          { label: "Batch ID", value: d.batch.batch_uuid.slice(0, 8), mono: true },
          { label: "Kiln / Device", value: d.batch.device_id ?? "—" },
          {
            label: "Credits",
            value: `${fmtCredit(d.batch.net_credit_t_co2e)} tCO₂e`,
            mono: true,
          },
        ]}
        warning="This is irreversible. The credit is recorded permanently in the registry and cannot be undone."
        confirmToken={`ISSUE-${d.batch.batch_uuid.slice(0, 6)}`}
        confirmLabel="Issue permanently"
        onConfirm={issue}
      />
    </div>
  );
}
