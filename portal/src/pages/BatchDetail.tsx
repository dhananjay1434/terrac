import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getBatch,
  issueCredit,
  downloadExport,
  AuthError,
  type BatchDetail as Detail,
  type MediaItem,
} from "../api";
import { getRole } from "../auth";
import ComplianceChecklist from "../components/ComplianceChecklist/ComplianceChecklist";
import EvidenceGallery from "../components/EvidenceGallery/EvidenceGallery";
import ConfirmModal from "../components/ConfirmModal/ConfirmModal";
import VerificationChain from "../components/VerificationChain/VerificationChain";
import MetricBlock from "../components/MetricBlock/MetricBlock";
import SealedVerdict from "../components/SealedVerdict/SealedVerdict";
import CopyButton from "../components/CopyButton/CopyButton";
import ProvenanceTile from "../components/ProvenanceTile/ProvenanceTile";
import LcaBreakdown from "../components/LcaBreakdown/LcaBreakdown";
import { fmtCredit } from "../format";

export const STEP_ORDER = [
  "batch_photo", "flame_curtain", "quenching", "flame_height",
  "smoke_0", "0", "smoke_50", "50", "smoke_90", "90", "smoke_100", "100",
  "lab_certificate",
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
  const [err, setErr] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);
  const [exporting, setExporting] = useState<"csi" | "rainbow" | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);

  function reload() {
    getBatch(uuid)
      .then(setD)
      .catch((e) => {
        if (e instanceof AuthError) nav("/login");
        else setErr("Batch not found.");
      });
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
      <div className="wrap err" style={{ textAlign: "center", paddingTop: 60 }}>
        <div className="text-primary" style={{ fontSize: 18, fontWeight: 600, marginBottom: 16 }}>Batch not found</div>
        <Link to="/batches" className="link-indigo">← All batches</Link>
      </div>
    );
  }
  if (!d) {
    return (
      <div className="wrap">
        <div className="skeleton" style={{ height: 180, borderRadius: "var(--r-lg)", marginBottom: 18 }}></div>
        <div className="tiles" style={{ marginBottom: 14 }}>
          <div className="skeleton" style={{ height: 72 }}></div>
          <div className="skeleton" style={{ height: 72 }}></div>
        </div>
        <div className="skeleton" style={{ height: 200, marginBottom: 14 }}></div>
        <div className="skeleton" style={{ height: 300 }}></div>
      </div>
    );
  }

  const okCount = d.compliance.checklist.filter((c) => c.ok).length;
  const total = d.compliance.checklist.length;
  const issued = d.batch.status === "ISSUED";
  const chainNodes = [
    {
      label: "Received",
      sublabel: d.batch.received_at
        ? d.batch.received_at.slice(0, 10)
        : undefined,
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
      <VerificationChain nodes={chainNodes} />
      <div className="hero">
        <div className="hero-verdict">
          <SealedVerdict
            size="lg"
            verdict={d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"}
            reasonCount={d.compliance.reasons.length}
          />
          <div className="credit-label">
            Batch <span className="mono">{d.batch.batch_uuid.slice(0, 8)}</span>{" "}
            <CopyButton value={d.batch.batch_uuid} label="Copy batch id" /> ·
            device {d.batch.device_id ?? "—"}
          </div>
          {issued ? (
            <div className="seal">✓ CREDIT ISSUED</div>
          ) : (
            getRole() === "admin" && (
              <button
                className="primary"
                style={{ marginTop: 16 }}
                disabled={!d.compliance.issuable || issuing}
                onClick={() => setConfirmOpen(true)}
              >
                {issuing
                  ? "Issuing…"
                  : d.compliance.issuable
                    ? "Issue credit"
                    : "Not yet issuable"}
              </button>
            )
          )}
          {getRole() === "admin" && d.compliance.issuable && (
            <div
              className="export-row"
              style={{ marginTop: 12, display: "flex", gap: 8 }}
            >
              <button
                className="neutral"
                disabled={exporting !== null}
                onClick={() => exportAs("csi")}
              >
                {exporting === "csi" ? "Exporting…" : "Export CSI"}
              </button>
              <button
                className="neutral"
                disabled={exporting !== null}
                onClick={() => exportAs("rainbow")}
              >
                {exporting === "rainbow" ? "Exporting…" : "Export Rainbow"}
              </button>
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
              <dd className="tabular">{d.batch.wet_yield_kg} kg</dd>
            </div>
            <div className="hero-fact">
              <dt className="micro">Project</dt>
              <dd>{d.batch.project_id ?? "—"}</dd>
            </div>
            <div className="hero-fact">
              <dt className="micro">Received</dt>
              <dd className="tabular">
                {d.batch.received_at?.slice(0, 10) ?? "—"}
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
        <ProvenanceTile
          batchUuid={d.batch.batch_uuid}
          deviceId={d.batch.device_id}
          projectId={d.batch.project_id}
          receivedAt={d.batch.received_at}
        />
      </div>

      <ComplianceChecklist checklist={d.compliance.checklist} />

      <EvidenceGallery media={d.media} />

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
          { label: "Methodology", value: "—" },
        ]}
        warning="This is irreversible. The credit is recorded permanently in the registry and cannot be undone."
        confirmToken={`ISSUE-${d.batch.batch_uuid.slice(0, 6)}`}
        confirmLabel="Issue permanently"
        danger
        onConfirm={issue}
      />
    </div>
  );
}
