import { useEffect, useState } from "react";
import { getUnboundSessions, bindSession, getDeviceSyncStatus } from "../api2";
import type { UnboundSession, SyncWatermark } from "../apiV2types";
import { getRole } from "../auth";
import Button from "../ui/Button/Button";
import Card from "../ui/Card/Card";

export default function UnboundSessions() {
  const [rows, setRows] = useState<UnboundSession[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [deviceId, setDeviceId] = useState("");
  const [marks, setMarks] = useState<SyncWatermark[] | null>(null);
  const isAdmin = getRole() === "admin";

  function reload() {
    setErr(null);
    getUnboundSessions().then((r) => setRows(r.unbound_sessions)).catch(() => setErr("Couldn't load unbound sessions."));
  }
  useEffect(reload, []);

  async function bind(sessionUuid: string) {
    const batchUuid = window.prompt("Bind session to which batch UUID?")?.trim();
    if (!batchUuid) return;
    setBusy(sessionUuid);
    try { await bindSession(sessionUuid, batchUuid); reload(); }
    catch { setErr(`Bind failed for ${sessionUuid.slice(0, 8)} — check the batch UUID exists.`); }
    finally { setBusy(null); }
  }
  async function loadWatermarks() {
    if (!deviceId.trim()) return;
    try { const r = await getDeviceSyncStatus(deviceId.trim()); setMarks(r.watermarks); }
    catch { setMarks([]); }
  }

  if (!isAdmin) return <div className="wrap">Admins only.</div>;
  return (
    <div className="wrap">
      <h1 className="text-primary" style={{ fontSize: 20, fontWeight: 600 }}>Unbound burn sessions</h1>
      <p className="micro" style={{ marginBottom: "var(--space-4)" }}>Burn sessions recorded with no batch yet. Bind each to attach its telemetry.</p>
      {err && <div className="err" style={{ marginBottom: "var(--space-3)" }}>{err}</div>}
      <Card as="section">
        {rows.length === 0 ? <div className="micro">No unbound sessions.</div> : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead><tr className="micro">
              <th style={{ textAlign: "left" }}>Session</th><th style={{ textAlign: "left" }}>Device</th>
              <th style={{ textAlign: "left" }}>Started</th><th style={{ textAlign: "right" }}>Chunks</th><th></th>
            </tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.session_uuid}>
                <td className="mono">{r.session_uuid.slice(0, 8)}</td>
                <td>{r.device_id ?? "—"}</td>
                <td className="tabular">{r.started_at ?? "—"}</td>
                <td className="tabular" style={{ textAlign: "right" }}>{r.chunk_count}</td>
                <td style={{ textAlign: "right" }}>
                  <Button size="sm" disabled={busy === r.session_uuid} onClick={() => bind(r.session_uuid)}>
                    {busy === r.session_uuid ? "Binding…" : "Bind to batch"}
                  </Button>
                </td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </Card>
      <Card as="section" style={{ marginTop: "var(--space-4)" }}>
        <span className="micro">Device sync status</span>
        <div style={{ display: "flex", gap: "var(--space-2)", margin: "var(--space-2) 0" }}>
          <input aria-label="device id" value={deviceId} onChange={(e) => setDeviceId(e.target.value)} placeholder="device id" style={{ flex: 1 }} />
          <Button size="sm" onClick={loadWatermarks}>Check</Button>
        </div>
        {marks && (marks.length === 0 ? <div className="micro">No watermarks for this device.</div> : (
          <ul className="micro">{marks.map((w) => (
            <li key={`${w.session_uuid}-${w.channel}`} className="mono">{w.session_uuid.slice(0, 8)} · {w.channel} · synced through seq {w.max_seq}</li>
          ))}</ul>
        ))}
      </Card>
    </div>
  );
}
