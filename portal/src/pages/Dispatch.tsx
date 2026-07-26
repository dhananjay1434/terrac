import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as Tabs from "@radix-ui/react-tabs";
import {
  listDispatch,
  listFacilities,
  createFacility,
  AuthError,
  ApiError,
  type DispatchRow,
  type FacilityRow,
} from "../api";
import { fmtDate, fmtPct } from "../format";
import { getRole } from "../auth";
import CardError from "../ui/CardError/CardError";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import EmptyState from "../components/EmptyState/EmptyState";
import StatusDot from "../components/StatusDot/StatusDot";
import StatusPill from "../ui/StatusPill/StatusPill";
import Card from "../ui/Card/Card";
import Button from "../ui/Button/Button";

const PAGE_SIZE = 25;

const VIEWS = {
  all: { label: "All", status: "" },
  draft: { label: "Draft", status: "draft" },
  in_transit: { label: "In-Transit", status: "in_transit" },
  received: { label: "Received", status: "received" },
} as const;
type ViewKey = keyof typeof VIEWS;


export default function Dispatch() {
  const nav = useNavigate();
  const [view, setView] = useState<ViewKey>("all");
  const [rows, setRows] = useState<DispatchRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [currentBefore, setCurrentBefore] = useState<string | null>(null);
  const [prevStack, setPrevStack] = useState<(string | null)[]>([]);
  const [pageIndex, setPageIndex] = useState(1);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [facilities, setFacilities] = useState<FacilityRow[]>([]);
  const [facilityUuid, setFacilityUuid] = useState("");
  const [facilityName, setFacilityName] = useState("");
  const [facilityType, setFacilityType] = useState<"artisanal" | "industrial">(
    "artisanal",
  );
  const [facilityMsg, setFacilityMsg] = useState<{ text: string; ok: boolean } | null>(
    null,
  );
  const [facilitySubmitting, setFacilitySubmitting] = useState(false);
  const [showFacilityForm, setShowFacilityForm] = useState(false);

  const fetchPage = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: String(PAGE_SIZE) };
        const statusFilter = VIEWS[view].status;
        if (statusFilter) params.status = statusFilter;
        if (before) params.before = before;
        const r = await listDispatch(params);
        setRows(r.dispatches);
        setNextCursor(r.next_cursor);
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load dispatches.");
      } finally {
        setLoading(false);
      }
    },
    [nav, view],
  );

  const fetchFacilities = useCallback(async () => {
    try {
      const r = await listFacilities({ limit: String(PAGE_SIZE) });
      setFacilities(r.facilities);
    } catch (_) {
      /* facility panel is supplementary; ignore background failure */
    }
  }, []);

  useEffect(() => {
    document.title = "Dispatch · TerraCipher";
    fetchFacilities();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setPrevStack([]);
    setCurrentBefore(null);
    setPageIndex(1);
    fetchPage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view]);

  useEffect(() => {
    if (!facilityMsg) return;
    const t = setTimeout(() => setFacilityMsg(null), 4000);
    return () => clearTimeout(t);
  }, [facilityMsg]);

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

  async function submitFacility(e: React.FormEvent) {
    e.preventDefault();
    if (!facilityUuid.trim() || !facilityName.trim()) {
      setFacilityMsg({ text: "Facility UUID and name are required", ok: false });
      return;
    }
    setFacilitySubmitting(true);
    setFacilityMsg(null);
    try {
      await createFacility({
        facility_uuid: facilityUuid.trim(),
        name: facilityName.trim(),
        facility_type: facilityType,
      });
      setFacilityMsg({ text: "✓ Facility registered", ok: true });
      setFacilityUuid("");
      setFacilityName("");
      await fetchFacilities();
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError && e.status === 409) {
        setFacilityMsg({ text: "A facility with that UUID already exists", ok: false });
      } else {
        setFacilityMsg({ text: "Registration failed — check values", ok: false });
      }
    } finally {
      setFacilitySubmitting(false);
    }
  }

  const columns: ColumnDef<DispatchRow>[] = [
    {
      key: "dispatch",
      header: "Dispatch",
      mono: true,
      render: (d) => d.dispatch_uuid.slice(0, 8),
    },
    { key: "kind", header: "Kind", render: (d) => d.kind },
    {
      key: "status",
      header: "Status",
      render: (d) => (
        <StatusDot
          variant={
            d.status === "received"
              ? "success"
              : d.status === "in_transit"
                ? "warning"
                : "inert"
          }
          label={d.status === "in_transit" ? "In transit" : d.status === "received" ? "Received" : "Draft"}
        />
      ),
    },
    {
      key: "weights",
      header: "Weight (source → facility)",
      align: "right",
      mono: true,
      render: (d) => (
        <>
          {d.weight_source_kg ?? "—"} → {d.weight_facility_kg ?? "—"} kg
          {d.weight_delta_pct != null && !d.weight_flagged && (
            <span className="micro">
              {" "}
              ({d.weight_delta_pct > 0 ? "+" : ""}
              {fmtPct(d.weight_delta_pct)})
            </span>
          )}
        </>
      ),
    },
    {
      key: "flag",
      header: "Reconciliation",
      render: (d) =>
        d.weight_flagged == null ? (
          <span className="text-tertiary">—</span>
        ) : d.weight_flagged ? (
          <StatusPill status="warning">
            Flagged ({d.weight_delta_pct?.toFixed(1)}%)
          </StatusPill>
        ) : (
          <StatusPill status="success">OK</StatusPill>
        ),
    },
    { key: "driver", header: "Driver", render: (d) => d.driver_name ?? "—" },
    { key: "truck", header: "Truck", render: (d) => d.truck_number ?? "—" },
    { key: "created", header: "Created", render: (d) => fmtDate(d.created_at) },
  ];

  return (
    <div className="wrap">
      <h1 className="page-title">Dispatch</h1>

      {getRole() === "admin" && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          <Button variant="neutral" size="sm" onClick={() => setShowFacilityForm((s) => !s)}>
            {showFacilityForm ? "Hide facility form" : "Register facility…"}
          </Button>
          {showFacilityForm && (
      <Card as="section" style={{ marginTop: "var(--space-3)" }}>
        <span className="micro">Register facility</span>
        <form className="filters" style={{ marginTop: 10 }} onSubmit={submitFacility}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="facility-uuid-input">
              Facility UUID
            </label>
            <input
              id="facility-uuid-input"
              aria-label="Facility UUID"
              value={facilityUuid}
              onChange={(e) => setFacilityUuid(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="facility-name-input">
              Name
            </label>
            <input
              id="facility-name-input"
              aria-label="Facility name"
              value={facilityName}
              onChange={(e) => setFacilityName(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="facility-type-select">
              Type
            </label>
            <select
              id="facility-type-select"
              aria-label="Facility type"
              value={facilityType}
              onChange={(e) =>
                setFacilityType(e.target.value as "artisanal" | "industrial")
              }
            >
              <option value="artisanal">Artisanal</option>
              <option value="industrial">Industrial</option>
            </select>
          </div>
          <Button
            type="submit"
            disabled={facilitySubmitting}
            style={{ alignSelf: "flex-end" }}
          >
            Save
          </Button>
        </form>
        {facilityMsg && (
          <div style={{ marginTop: 12 }}>
            <StatusPill status={facilityMsg.ok ? "success" : "error"}>
              {facilityMsg.text}
            </StatusPill>
          </div>
        )}
        {facilities.length > 0 && (
          <div className="micro text-secondary" style={{ marginTop: 10 }}>
            {facilities.length} facilit{facilities.length === 1 ? "y" : "ies"}{" "}
            registered.
          </div>
        )}
      </Card>
          )}
        </div>
      )}

      <Tabs.Root value={view} onValueChange={(v) => setView(v as ViewKey)}>
        <Tabs.List
          aria-label="Dispatch status"
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
        {(Object.keys(VIEWS) as ViewKey[]).map((k) => (
          <Tabs.Content key={k} value={k} />
        ))}
      </Tabs.Root>

      {err && (
        <CardError message={err} onRetry={() => fetchPage(currentBefore)} />
      )}

      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(d) => d.dispatch_uuid}
        loading={loading}
        empty={
          <EmptyState
            title="No dispatches found"
            description="Adjust the filter above, or wait for field devices to sync."
          />
        }
      />

      <nav className="pager" aria-label="Dispatch pagination">
        <Button
          variant="neutral"
          size="sm"
          onClick={goPrev}
          disabled={loading || prevStack.length === 0}
        >
          ‹ Previous
        </Button>
        <span className="micro pager-status" aria-live="polite">
          Page {pageIndex}
          {rows.length > 0 &&
            ` · ${rows.length} row${rows.length === 1 ? "" : "s"}`}
        </span>
        <Button
          variant="neutral"
          size="sm"
          onClick={goNext}
          disabled={loading || !nextCursor}
        >
          Next ›
        </Button>
      </nav>
    </div>
  );
}
