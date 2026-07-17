import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  getBatch,
  fetchMediaUrl,
  issueCredit,
  downloadExport,
  AuthError,
  type BatchDetail as Detail,
  type MediaItem,
} from "../api";
import { getRole } from "../auth";
import ComplianceChecklist from "../components/ComplianceChecklist";
import CreditRing from "../components/CreditRing";

const STEP_ORDER = [
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
  smoke_20: "Smoke opacity — 20%", "20": "Smoke opacity — 20%",
  smoke_40: "Smoke opacity — 40%", "40": "Smoke opacity — 40%",
  smoke_60: "Smoke opacity — 60%", "60": "Smoke opacity — 60%",
  smoke_80: "Smoke opacity — 80%", "80": "Smoke opacity — 80%",
  smoke_100: "Smoke opacity — 100%", "100": "Smoke opacity — 100%",
  post_burn_mass: "Post-burn mass",
  packaging: "Packaging",
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

function MediaThumb({ item }: { item: MediaItem }) {
  const [url, setUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    let live = true;
    let objUrl: string | null = null;
    fetchMediaUrl(item.operation_id)
      .then((u) => {
        objUrl = u;
        if (live) setUrl(u);
      })
      .catch(() => {});
    return () => {
      live = false;
      if (objUrl) URL.revokeObjectURL(objUrl);
    };
  }, [item.operation_id]);
  return (
    <div className="media-cell">
      {url ? (
        <img src={url} alt={item.filename ?? item.operation_id} />
      ) : (
        <div
          style={{
            height: 90,
            display: "grid",
            placeItems: "center",
            background: "var(--surface-page)",
          }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--text-tertiary)" strokeWidth="2">
            <path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
        </div>
      )}
      <div className="forensic-meta">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span className="mono">{item.sha256_hash.slice(0, 12)}…</span>
          <button
            aria-label="Copy SHA-256"
            className="linkbtn"
            onClick={() => {
              navigator.clipboard.writeText(item.sha256_hash);
              setCopied(true);
              setTimeout(() => setCopied(false), 1500);
            }}
          >
            {copied ? "✓" : "📋"}
          </button>
        </div>
        {item.uploaded_at && (
          <div style={{ color: "var(--text-tertiary)" }}>
            {item.uploaded_at.slice(0, 16).replace("T", " ")}
          </div>
        )}
        <div>
          {item.exif_lat !== null && item.exif_lon !== null ? (
            <a
              href={`https://www.openstreetmap.org/?mlat=${item.exif_lat}&mlon=${item.exif_lon}#map=17/${item.exif_lat}/${item.exif_lon}`}
              target="_blank"
              rel="noreferrer"
            >
              {item.exif_lat.toFixed(5)}, {item.exif_lon.toFixed(5)}
            </a>
          ) : (
            <span style={{ color: "var(--text-tertiary)" }}>no GPS</span>
          )}
        </div>
        <div style={{ marginTop: 4 }}>
          {item.capture_type_verified ? (
            <span className="chip ok">✓ verified</span>
          ) : item.capture_type ? (
            <span className="chip warn">unverified</span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function BatchDetail() {
  const { uuid = "" } = useParams();
  const nav = useNavigate();
  const [d, setD] = useState<Detail | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [issuing, setIssuing] = useState(false);
  const [exporting, setExporting] = useState<"csi" | "rainbow" | null>(null);

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmText, setConfirmText] = useState("");

  function reload() {
    getBatch(uuid)
      .then(setD)
      .catch((e) => {
        if (e instanceof AuthError) nav("/login");
        else setErr("Batch not found.");
      });
  }
  useEffect(reload, [uuid, nav]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setConfirmOpen(false);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, []);

  async function issue() {
    if (!d || confirmText !== "ISSUE") return;
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
        <div style={{ fontSize: 18, fontWeight: 600, color: "var(--text-primary)", marginBottom: 16 }}>Batch not found</div>
        <Link to="/batches" style={{ color: "var(--indigo-600)", textDecoration: "none" }}>← All batches</Link>
      </div>
    );
  }
  if (!d) {
    return (
      <div className="wrap">
        <div className="skeleton" style={{ height: 180, borderRadius: "var(--radius-lg)", marginBottom: 18 }}></div>
        <div className="tiles" style={{ marginBottom: 14 }}>
          <div className="skeleton" style={{ height: 72 }}></div>
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

  return (
    <div className="wrap">
      <Link className="back" to="/batches">
        ← All batches
      </Link>
      <div className="hero" style={{ marginTop: 12 }}>
        <div>
          <span
            className={`verdict ${d.compliance.issuable ? "iss" : "prov"}`}
          >
            {d.compliance.issuable ? "ISSUABLE" : "PROVISIONAL"}
          </span>
          <div className="credit">
            <span className="num tabular">
              {d.batch.net_credit_t_co2e.toFixed(2)}
            </span>
            <span className="unit">tCO₂e</span>
          </div>
          <div className="credit-label">
            Batch {d.batch.batch_uuid.slice(0, 8)} · device{" "}
            {d.batch.device_id ?? "—"}
          </div>
          {d.batch.status === "ISSUED" ? (
            <div className="seal">✓ CREDIT ISSUED</div>
          ) : (
            getRole() === "admin" && (
              <button
                className="primary"
                style={{ marginTop: 16 }}
                disabled={!d.compliance.issuable || issuing}
                onClick={() => {
                  setConfirmText("");
                  setConfirmOpen(true);
                }}
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
        <CreditRing okCount={okCount} total={total} />
      </div>

      <div className="tiles">
        {Object.entries(d.evidence_counts).map(([k, v]) => (
          <div className="card tile" key={k}>
            <span className="micro">{k.replace(/_/g, " ")}</span>
            <div className="v tabular">{v}</div>
          </div>
        ))}
      </div>

      <ComplianceChecklist checklist={d.compliance.checklist} />

      {d.media.length > 0 && (
        <section className="card" style={{ marginTop: 14 }}>
          <span className="micro">Evidence media</span>
          <div style={{ marginTop: 12 }}>
            {groupMedia(d.media).map(([stage, items]) => (
              <div key={stage} className="evidence-group">
                <div className="evidence-group-head">
                  <h3>
                    {stage === '__unclassified__' ? STEP_TITLES['other'] : STEP_TITLES[stage] ?? stage}
                  </h3>
                  <div className="chip">{items.length}</div>
                </div>
                <div className="media-grid">
                  {items.map(m => (
                    <MediaThumb key={m.sha256_hash} item={m} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {confirmOpen && (
        <div className="modal-overlay" onClick={() => setConfirmOpen(false)}>
          <div className="modal-panel" onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
            <h2>Issue credit — permanent</h2>
            <p>You are about to permanently issue {d.batch.net_credit_t_co2e.toFixed(2)} tCO₂e to batch {d.batch.batch_uuid.slice(0, 8)}. This writes to the permanent ledger and cannot be undone.</p>
            <label className="micro">Type ISSUE to confirm</label>
            <input value={confirmText} onChange={e => setConfirmText(e.target.value)} style={{ width: '100%', marginTop: 4, marginBottom: 16 }} />
            <div className="modal-actions">
              <button className="neutral" onClick={() => setConfirmOpen(false)}>Cancel</button>
              <button className="primary" disabled={confirmText !== "ISSUE" || issuing} onClick={issue}>Issue permanently</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
