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
          {/* MEDIA GALLERY REPLACEMENT START */}
          <div className="space-y-6" style={{ marginTop: 12 }}>
            {['lab_certificate', 'batch_photo', 'flame_curtain', 'quench'].map(stage => {
              const stageMedia = d.media.filter(m => m.capture_type === stage);
              if (stageMedia.length === 0) return null;
              
              return (
                <div key={stage} className="border rounded-md p-4 bg-gray-50" style={{ border: '1px solid #ddd', padding: 12, marginBottom: 12, borderRadius: 6 }}>
                  <h3 className="font-semibold text-lg mb-4 capitalize" style={{ textTransform: 'capitalize', marginBottom: 8, fontSize: 14 }}>
                    {stage.replace('_', ' ')}
                  </h3>
                  <div className="media-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 12 }}>
                    {stageMedia.map(m => (
                      <div key={m.sha256_hash} className="border rounded bg-white shadow-sm overflow-hidden" style={{ border: '1px solid #eee', borderRadius: 4, overflow: 'hidden' }}>
                        <a href={`/api/v1/media/${m.sha256_hash}`} target="_blank" rel="noreferrer">
                          <img 
                            src={`/api/v1/media/${m.sha256_hash}`} 
                            alt="Evidence" 
                            className="w-full h-32 object-cover"
                            style={{ width: '100%', height: 100, objectFit: 'cover' }} 
                          />
                        </a>
                        <div className="p-2 text-xs text-gray-600" style={{ padding: 8, fontSize: 11 }}>
                          <p><strong>SHA256:</strong> {m.sha256_hash?.substring(0,8)}...</p>
                          <p>
                            <strong>Status:</strong> {m.capture_type_verified 
                              ? <span style={{ color: 'green' }}>Verified (Signed)</span>
                              : <span style={{ color: 'orange' }}>Unverified (Hint)</span>}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
            
            {/* UNKNOWN / OTHER */}
            {d.media.filter(m => !['lab_certificate', 'batch_photo', 'flame_curtain', 'quench'].includes(m.capture_type ?? '')).length > 0 && (
              <div className="border rounded-md p-4 bg-gray-50 mt-8" style={{ border: '1px solid #ddd', padding: 12, marginBottom: 12, borderRadius: 6 }}>
                <h3 className="font-semibold text-lg mb-4 text-gray-700" style={{ marginBottom: 8, fontSize: 14 }}>Other / Uncategorized</h3>
                <div className="media-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 12 }}>
                  {d.media.filter(m => !['lab_certificate', 'batch_photo', 'flame_curtain', 'quench'].includes(m.capture_type ?? '')).map(m => (
                    <div key={m.sha256_hash} className="border rounded bg-white shadow-sm overflow-hidden" style={{ border: '1px solid #eee', borderRadius: 4, overflow: 'hidden' }}>
                      <a href={`/api/v1/media/${m.sha256_hash}`} target="_blank" rel="noreferrer">
                        <img 
                          src={`/api/v1/media/${m.sha256_hash}`} 
                          alt="Evidence" 
                          className="w-full h-32 object-cover" 
                          style={{ width: '100%', height: 100, objectFit: 'cover' }}
                        />
                      </a>
                      <div className="p-2 text-xs text-gray-600" style={{ padding: 8, fontSize: 11 }}>
                        <p><strong>SHA256:</strong> {m.sha256_hash?.substring(0,8)}...</p>
                        <p style={{ color: '#888' }}>Uncategorized</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
          {/* MEDIA GALLERY REPLACEMENT END */}
        </section>
      )}
    </div>
  );
}
