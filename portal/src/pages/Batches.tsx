import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { listBatches, AuthError, type BatchRow } from "../api";

function shortId(uuid: string) {
  return uuid.slice(0, 8);
}
function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : "—";
}

export default function Batches() {
  const nav = useNavigate();
  const [rows, setRows] = useState<BatchRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [status, setStatus] = useState("");
  const [provisional, setProvisional] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(
    async (reset: boolean) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: "50" };
        if (status) params.status = status;
        if (provisional) params.provisional = provisional;
        if (!reset && cursor) params.before = cursor;
        const r = await listBatches(params);
        setRows((prev) => (reset ? r.batches : [...prev, ...r.batches]));
        setCursor(r.next_cursor);
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load batches.");
      } finally {
        setLoading(false);
      }
    },
    [status, provisional, cursor, nav],
  );

  // Reload from scratch whenever a filter changes.
  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, provisional]);

  useEffect(() => {
    document.title = "Batches · TerraCipher";
  }, []);

  return (
    <div className="wrap">
      <div className="filters">
        <span className="select-wrap">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="RECEIVED">RECEIVED</option>
            <option value="ISSUED">ISSUED</option>
          </select>
        </span>
        <span className="select-wrap">
          <select
            value={provisional}
            onChange={(e) => setProvisional(e.target.value)}
          >
            <option value="">Provisional &amp; issuable</option>
            <option value="true">Provisional only</option>
            <option value="false">Issuable only</option>
          </select>
        </span>
      </div>

      {err && <div className="err">{err}</div>}

      <table>
        <thead>
          <tr>
            <th>Batch</th>
            <th>Device</th>
            <th>Received</th>
            <th className="num-col">Credit (tCO₂e)</th>
            <th>Status</th>
            <th>Flags</th>
          </tr>
        </thead>
        <tbody>
          {loading && rows.length === 0 ? (
            Array.from({ length: 5 }).map((_, i) => (
              <tr key={i}>
                <td colSpan={6}>
                  <div className="skeleton" style={{ height: 14, margin: '8px 0' }}></div>
                </td>
              </tr>
            ))
          ) : rows.length === 0 ? (
            <tr>
              <td colSpan={6} style={{ padding: '60px 20px', textAlign: 'center' }}>
                <div style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 8 }}>
                  No batches found
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                  Adjust the filters above, or wait for field devices to sync.
                </div>
              </td>
            </tr>
          ) : (
            rows.map((b) => (
              <tr
                key={b.batch_uuid}
                onClick={() => nav(`/batches/${b.batch_uuid}`)}
              >
                <td className="tabular">{shortId(b.batch_uuid)}</td>
                <td>{b.device_id ?? "—"}</td>
                <td className="tabular">{fmtDate(b.received_at)}</td>
                <td className="tabular num-col">{b.net_credit_t_co2e.toFixed(3)}</td>
                <td>
                  <span className={`badge ${b.provisional ? "prov" : "iss"}`}>
                    {b.provisional ? "PROVISIONAL" : "ISSUABLE"}
                  </span>
                </td>
                <td>
                  {b.reason_count > 0 ? (
                    <span className="chip warn">{b.reason_count} reason{b.reason_count === 1 ? "" : "s"}</span>
                  ) : (
                    <span style={{ color: "var(--text-tertiary)" }}>—</span>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>

      {cursor && (
        <button
          className="primary"
          style={{ marginTop: 16 }}
          onClick={() => load(false)}
          disabled={loading}
        >
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
    </div>
  );
}
