import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import * as Tabs from "@radix-ui/react-tabs";
import { Copy, Check, ChevronRight } from "lucide-react";
import { listBatches, AuthError, type BatchRow } from "../api";
import { getRole } from "../auth";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import FilterBar, { type FilterPatch } from "../components/FilterBar/FilterBar";
import StatusDot from "../components/StatusDot/StatusDot";
import EmptyState from "../components/EmptyState/EmptyState";

function shortId(uuid: string) {
  return uuid.slice(0, 8);
}
function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : "—";
}

// Saved views: each maps to a fixed server-filter combo. "blocking"
// additionally narrows client-side to rows with blockers.
const VIEWS = {
  all: { label: "All", status: "", provisional: "" },
  awaiting: { label: "Awaiting review", status: "RECEIVED", provisional: "" },
  blocking: { label: "Blocking issues", status: "", provisional: "true" },
  issued: { label: "Issued", status: "ISSUED", provisional: "" },
} as const;
type ViewKey = keyof typeof VIEWS;

function CopyId({ uuid }: { uuid: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      className="linkbtn"
      type="button"
      aria-label="Copy batch id"
      onClick={(e) => {
        e.stopPropagation();
        navigator.clipboard.writeText(uuid);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
    </button>
  );
}

export default function Batches() {
  const nav = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const rawView = searchParams.get("view") ?? "all";
  const view: ViewKey = rawView in VIEWS ? (rawView as ViewKey) : "all";

  const [rows, setRows] = useState<BatchRow[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<string>(() => VIEWS[view].status);
  const [provisional, setProvisional] = useState<string>(
    () => VIEWS[view].provisional,
  );
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
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

  function switchView(v: ViewKey) {
    setSearchParams(v === "all" ? {} : { view: v });
    setStatus(VIEWS[v].status);
    setProvisional(VIEWS[v].provisional);
    setSearch("");
  }

  function onFilter(p: FilterPatch) {
    if (p.kind === "search") setSearch(p.value);
    else if (p.kind === "status") setStatus(p.value);
    else if (p.kind === "provisional") setProvisional(p.value);
    else {
      setSearch("");
      setStatus(VIEWS[view].status);
      setProvisional(VIEWS[view].provisional);
    }
  }

  function toggleSelect(id: string) {
    setSelected((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const q = search.trim().toLowerCase();
  const displayed = rows
    .filter(
      (b) =>
        !q ||
        b.batch_uuid.toLowerCase().includes(q) ||
        (b.device_id ?? "").toLowerCase().includes(q),
    )
    .filter((b) => view !== "blocking" || b.reason_count > 0);

  const columns: ColumnDef<BatchRow>[] = [
    {
      key: "select",
      header: "",
      width: "36px",
      render: (b) => (
        <input
          type="checkbox"
          aria-label={`Select batch ${shortId(b.batch_uuid)}`}
          checked={selected.has(b.batch_uuid)}
          onClick={(e) => e.stopPropagation()}
          onChange={() => toggleSelect(b.batch_uuid)}
        />
      ),
    },
    {
      key: "batch",
      header: "Batch",
      mono: true,
      render: (b) => (
        <span>
          {shortId(b.batch_uuid)} <CopyId uuid={b.batch_uuid} />
        </span>
      ),
    },
    { key: "device", header: "Device", render: (b) => b.device_id ?? "—" },
    {
      key: "received",
      header: "Received",
      render: (b) => fmtDate(b.received_at),
    },
    {
      key: "credit",
      header: "Credit (tCO₂e)",
      align: "right",
      mono: true,
      render: (b) => b.net_credit_t_co2e.toFixed(3),
    },
    {
      key: "status",
      header: "Status",
      render: (b) => (
        <StatusDot
          variant={b.provisional ? "warning" : "success"}
          label={b.provisional ? "Provisional" : "Issuable"}
        />
      ),
    },
    {
      key: "flags",
      header: "Blockers",
      render: (b) =>
        b.reason_count > 0 ? (
          <span className="chip warn">
            {b.reason_count} reason{b.reason_count === 1 ? "" : "s"}
          </span>
        ) : (
          <span className="text-tertiary">—</span>
        ),
    },
    {
      key: "open",
      header: "",
      width: "32px",
      render: () => (
        <span className="text-tertiary">
          <ChevronRight size={14} aria-hidden />
        </span>
      ),
    },
  ];

  return (
    <div className="wrap">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: 16,
        }}
      >
        <h1 style={{ fontSize: 20 }}>Batches</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="neutral" disabled title="Export coming soon">
            Export CSV
          </button>
          {getRole() === "admin" && (
            <button
              className="neutral"
              disabled
              title="Batches sync from field devices"
            >
              New batch
            </button>
          )}
        </div>
      </div>

      <Tabs.Root value={view} onValueChange={(v) => switchView(v as ViewKey)}>
        <Tabs.List
          aria-label="Saved views"
          style={{ display: "flex", gap: 4, marginBottom: 12 }}
        >
          {(Object.keys(VIEWS) as ViewKey[]).map((k) => (
            <Tabs.Trigger
              key={k}
              value={k}
              className={`linkbtn ${view === k ? "active" : ""}`}
            >
              {VIEWS[k].label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {/* Panels must exist for the triggers' aria-controls; the actual
            table lives below and is shared by every view. */}
        {(Object.keys(VIEWS) as ViewKey[]).map((k) => (
          <Tabs.Content key={k} value={k} />
        ))}
      </Tabs.Root>

      <FilterBar
        value={{ search, status, provisional }}
        onChange={onFilter}
      />

      {err && (
        <div
          className="card"
          style={{
            borderColor: "var(--status-error-fg)",
            marginBottom: 16,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span className="err" style={{ margin: 0 }}>
            {err}
          </span>
          <button className="neutral" type="button" onClick={() => load(true)}>
            Retry
          </button>
        </div>
      )}

      {selected.size > 0 && (
        <div
          className="card"
          style={{
            padding: 10,
            marginBottom: 12,
            display: "flex",
            gap: 12,
            alignItems: "center",
          }}
        >
          <span className="micro">{selected.size} selected</span>
          <button
            className="neutral"
            disabled
            title="Bulk actions arrive in a later phase"
          >
            Export selected
          </button>
        </div>
      )}

      <DataTable
        columns={columns}
        rows={displayed}
        rowKey={(b) => b.batch_uuid}
        onRowClick={(b) => nav(`/batches/${b.batch_uuid}`)}
        loading={loading}
        empty={
          <EmptyState
            title="No batches found"
            description="Adjust the filters above, or wait for field devices to sync."
          />
        }
      />

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 12,
        }}
      >
        <span className="micro">
          Showing {displayed.length} row{displayed.length === 1 ? "" : "s"}
        </span>
        {cursor && (
          <button
            className="linkbtn"
            type="button"
            onClick={() => load(false)}
            disabled={loading}
          >
            {loading ? "Loading…" : "Load more"}
          </button>
        )}
      </div>
    </div>
  );
}
