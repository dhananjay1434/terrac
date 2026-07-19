import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import * as Tabs from "@radix-ui/react-tabs";
import { Copy, Check, ChevronRight } from "lucide-react";
import { listBatches, getSummary, AuthError, type BatchRow } from "../api";
import { fmtCredit } from "../format";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import FilterBar, { type FilterPatch } from "../components/FilterBar/FilterBar";
import StatusDot from "../components/StatusDot/StatusDot";
import EmptyState from "../components/EmptyState/EmptyState";
import StatTile from "../components/StatTile/StatTile";
import InfoTip from "../components/InfoTip/InfoTip";

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
const NO_VIEW = "custom";

// The active tab must always reflect actual filter state — never the URL —
// so a tab can never be highlighted while the selects disagree with it.
function viewFromFilters(status: string, provisional: string): ViewKey | null {
  return (
    (Object.keys(VIEWS) as ViewKey[]).find(
      (k) => VIEWS[k].status === status && VIEWS[k].provisional === provisional,
    ) ?? null
  );
}

// Fixed page size for cursor pagination — each page is one listBatches call,
// so memory is O(PAGE_SIZE) regardless of how many batches exist in total.
const PAGE_SIZE = 25;

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
  const initialRawView = searchParams.get("view") ?? "all";
  const initialView: ViewKey =
    initialRawView in VIEWS ? (initialRawView as ViewKey) : "all";

  const [rows, setRows] = useState<BatchRow[]>([]);
  // Current page only — never accumulated — so memory stays O(PAGE_SIZE).
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  // The "before" cursor that produced the CURRENTLY visible page (null on
  // page 1). prevStack holds the "before" cursors of every earlier page so
  // "Previous" can pop back through them without re-deriving anything.
  const [currentBefore, setCurrentBefore] = useState<string | null>(null);
  const [prevStack, setPrevStack] = useState<(string | null)[]>([]);
  const [pageIndex, setPageIndex] = useState(1);
  const [status, setStatus] = useState<string>(() => VIEWS[initialView].status);
  const [provisional, setProvisional] = useState<string>(
    () => VIEWS[initialView].provisional,
  );
  // Derived, never read back from the URL: the tab highlight can never
  // contradict the selects, because it IS the selects' current combo.
  const view = viewFromFilters(status, provisional);
  const [search, setSearch] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<Awaited<
    ReturnType<typeof getSummary>
  > | null>(null);

  const fetchPage = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: String(PAGE_SIZE) };
        if (status) params.status = status;
        if (provisional) params.provisional = provisional;
        if (before) params.before = before;
        const r = await listBatches(params);
        setRows(r.batches);
        setNextCursor(r.next_cursor);
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load batches.");
      } finally {
        setLoading(false);
      }
    },
    [status, provisional, nav],
  );

  // Reload from scratch (back to page 1, fresh cursor stack) whenever a
  // filter changes. The URL mirrors the resolved view (or drops the param
  // for "all"/no match) — it is written FROM state, never read back into it,
  // so it can't drift out of sync.
  useEffect(() => {
    setPrevStack([]);
    setCurrentBefore(null);
    setPageIndex(1);
    fetchPage(null);
    setSearchParams(view && view !== "all" ? { view } : {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, provisional]);

  function goNext() {
    if (!nextCursor) return;
    setPrevStack((s) => [...s, currentBefore]);
    setCurrentBefore(nextCursor);
    setPageIndex((n) => n + 1);
    fetchPage(nextCursor);
  }
  function goPrev() {
    setPrevStack((s) => {
      const copy = [...s];
      const target = copy.pop() ?? null;
      setCurrentBefore(target);
      setPageIndex((n) => Math.max(1, n - 1));
      fetchPage(target);
      return copy;
    });
  }

  useEffect(() => {
    document.title = "Batches · TerraCipher";
  }, []);

  // Fire-and-forget: the summary band is a supplementary signal, not the
  // page's primary data source, so a failure here must never block the
  // table or trigger a redirect — fetchPage() already owns AuthError handling.
  useEffect(() => {
    getSummary()
      .then(setSummary)
      .catch(() => {});
  }, []);

  function switchView(v: ViewKey) {
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
      setStatus(VIEWS.all.status);
      setProvisional(VIEWS.all.provisional);
    }
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
      render: (b) => fmtCredit(b.net_credit_t_co2e),
    },
    {
      key: "status",
      header: (
        <>
          Status
          <InfoTip label="Issuable = all compliance gates met and ready to issue. Provisional = one or more gates unmet." />
        </>
      ),
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
      <h1 className="page-title">Batches</h1>

      {summary && (
        <div className="stat-band">
          <StatTile label="Issued" value={String(summary.by_status["ISSUED"] ?? 0)} />
          <StatTile
            label="Received / in review"
            value={String(summary.by_status["RECEIVED"] ?? 0)}
          />
          <StatTile label="Provisional" value={String(summary.provisional)} />
          <StatTile
            label="Credit"
            value={fmtCredit(
              rows.reduce((sum, b) => sum + b.net_credit_t_co2e, 0),
            )}
            hint="this page"
          />
        </div>
      )}

      <Tabs.Root
        value={view ?? NO_VIEW}
        onValueChange={(v) => switchView(v as ViewKey)}
      >
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
            table lives below and is shared by every view. A hidden extra
            panel backs NO_VIEW so Tabs.Root never renders zero active tabs
            when the selects diverge from every saved combo. */}
        {(Object.keys(VIEWS) as ViewKey[]).map((k) => (
          <Tabs.Content key={k} value={k} />
        ))}
        <Tabs.Content value={NO_VIEW} />
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
          <button
            className="neutral"
            type="button"
            onClick={() => fetchPage(currentBefore)}
          >
            Retry
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
          q && rows.length > 0 ? (
            <EmptyState
              title="No matches on this page"
              description="Search filters the current page only. Clear the search to page through all results."
            />
          ) : (
            <EmptyState
              title="No batches found"
              description="Adjust the filters above, or wait for field devices to sync."
            />
          )
        }
      />

      <nav className="pager" aria-label="Batches pagination">
        <button
          className="neutral"
          type="button"
          onClick={goPrev}
          disabled={loading || prevStack.length === 0}
        >
          ‹ Previous
        </button>
        <span className="micro pager-status" aria-live="polite">
          Page {pageIndex}
          {rows.length > 0 &&
            ` · ${rows.length} row${rows.length === 1 ? "" : "s"}`}
        </span>
        <button
          className="neutral"
          type="button"
          onClick={goNext}
          disabled={loading || !nextCursor}
        >
          Next ›
        </button>
      </nav>
    </div>
  );
}
