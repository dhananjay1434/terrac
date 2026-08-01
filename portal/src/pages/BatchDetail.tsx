import { Link, useParams } from "react-router-dom";
import type { MediaItem } from "../api";
import { getRole } from "../auth";
import { useBatchDetail } from "../features/batch-detail/useBatchDetail";
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
  const {
    d,
    timeline,
    timelineLightbox,
    setTimelineLightbox,
    err,
    issuing,
    exporting,
    confirmOpen,
    setConfirmOpen,
    reload,
    issue,
    exportAs,
    showTimeline,
    showThermal,
    showLoad,
    chainNodes,
  } = useBatchDetail(uuid);

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

  const issued = d.batch.status === "ISSUED";

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
          <StatTile label="Min temp" value={showThermal && d.telemetry?.min_temp != null ? `${d.telemetry.min_temp}°C` : "—"} />
          <StatTile label="Max temp" value={showThermal && d.telemetry?.max_temp != null ? `${d.telemetry.max_temp}°C` : "—"} />
          <StatTile label="Load channel" value={showLoad ? "active" : "—"} />
          {/* Weight is a single post-burn measurement, not a time series —
              shown as a stat, not a curve. A weight-vs-time curve would
              require app-side series capture (out of scope). */}
          <StatTile label="Post-burn yield" value={fmtKg(d.batch.wet_yield_kg)} />
        </div>
      </Card>

      {showTimeline && timeline.length > 0 && (
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
