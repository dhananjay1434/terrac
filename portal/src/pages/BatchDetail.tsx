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

function MediaThumb({ item }: { item: MediaItem }) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let live = true;
    let objUrl: string | null = null;
    fetchMediaUrl(item.operation_id)
      .then((u) => {
        objUrl = u;
        if (live) setUrl(u);
      })
      .catch(() => live && setFailed(true));
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
            color: "var(--faint)",
            fontSize: 11,
          }}
        >
          {failed ? "unavailable" : "loading…"}
        </div>
      )}
      <div className="cap tabular">{item.sha256_hash.slice(0, 12)}…</div>
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

  function reload() {
    getBatch(uuid)
      .then(setD)
      .catch((e) => {
        if (e instanceof AuthError) nav("/login");
        else setErr("Batch not found.");
      });
  }
  useEffect(reload, [uuid, nav]);

  async function issue() {
    if (!d) return;
    if (
      !window.confirm(
        `Issue ${d.batch.net_credit_t_co2e.toFixed(2)} tCO₂e for batch ` +
          `${d.batch.batch_uuid.slice(0, 8)}? This is recorded permanently.`,
      )
    )
      return;
    setIssuing(true);
    try {
      await issueCredit(uuid);
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

  if (err) return <div className="wrap err">{err}</div>;
  if (!d) return <div className="wrap">Loading…</div>;

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
                onClick={issue}
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
          <div className="media-grid">
            {d.media.map((m) => (
              <MediaThumb key={m.operation_id} item={m} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
