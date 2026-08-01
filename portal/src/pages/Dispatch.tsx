import * as Tabs from "@radix-ui/react-tabs";
import { fmtDate, fmtPct } from "../format";
import { getRole } from "../auth";
import CardError from "../ui/CardError/CardError";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import EmptyState from "../components/EmptyState/EmptyState";
import StatusDot from "../components/StatusDot/StatusDot";
import StatusPill from "../ui/StatusPill/StatusPill";
import Card from "../ui/Card/Card";
import Button from "../ui/Button/Button";
import Skeleton from "../components/Skeleton/Skeleton";
import JourneyPanel from "../components/JourneyPanel/JourneyPanel";
import { useDispatch, DISPATCH_VIEWS, type DispatchViewKey } from "../features/dispatch/useDispatch";
import type { DispatchRow } from "../api";

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

export default function Dispatch() {
  const dp = useDispatch();

  return (
    <div className="wrap">
      <h1 className="page-title">Dispatch</h1>

      {getRole() === "admin" && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          <Button variant="neutral" size="sm" onClick={() => dp.setShowFacilityForm((s) => !s)}>
            {dp.showFacilityForm ? "Hide facility form" : "Register facility…"}
          </Button>
          {dp.showFacilityForm && (
            <Card as="section" style={{ marginTop: "var(--space-3)" }}>
              <span className="micro">Register facility</span>
              <form className="filters" style={{ marginTop: "var(--space-3)" }} onSubmit={dp.submitFacility}>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                  <label className="micro" htmlFor="facility-uuid-input">
                    Facility UUID
                  </label>
                  <input
                    id="facility-uuid-input"
                    aria-label="Facility UUID"
                    value={dp.facilityUuid}
                    onChange={(e) => dp.setFacilityUuid(e.target.value)}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                  <label className="micro" htmlFor="facility-name-input">
                    Name
                  </label>
                  <input
                    id="facility-name-input"
                    aria-label="Facility name"
                    value={dp.facilityName}
                    onChange={(e) => dp.setFacilityName(e.target.value)}
                  />
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "var(--space-1)" }}>
                  <label className="micro" htmlFor="facility-type-select">
                    Type
                  </label>
                  <select
                    id="facility-type-select"
                    aria-label="Facility type"
                    value={dp.facilityType}
                    onChange={(e) =>
                      dp.setFacilityType(e.target.value as "artisanal" | "industrial")
                    }
                  >
                    <option value="artisanal">Artisanal</option>
                    <option value="industrial">Industrial</option>
                  </select>
                </div>
                <Button
                  type="submit"
                  disabled={dp.facilitySubmitting}
                  style={{ alignSelf: "flex-end" }}
                >
                  Save
                </Button>
              </form>
              {dp.facilityMsg && (
                <div style={{ marginTop: "var(--space-3)" }}>
                  <StatusPill status={dp.facilityMsg.ok ? "success" : "error"}>
                    {dp.facilityMsg.text}
                  </StatusPill>
                </div>
              )}
              {dp.facilities.length > 0 && (
                <div className="micro text-secondary" style={{ marginTop: "var(--space-3)" }}>
                  {dp.facilities.length} facilit{dp.facilities.length === 1 ? "y" : "ies"}{" "}
                  registered.
                </div>
              )}
            </Card>
          )}
        </div>
      )}

      <Tabs.Root value={dp.view} onValueChange={(v) => dp.setView(v as DispatchViewKey)}>
        <Tabs.List
          aria-label="Dispatch status"
          style={{ display: "flex", gap: "var(--space-1)", marginBottom: "var(--space-3)" }}
        >
          {(Object.keys(DISPATCH_VIEWS) as DispatchViewKey[]).map((k) => (
            <Tabs.Trigger
              key={k}
              value={k}
              className={`linkbtn ${dp.view === k ? "active" : ""}`}
            >
              {DISPATCH_VIEWS[k].label}
            </Tabs.Trigger>
          ))}
        </Tabs.List>
        {(Object.keys(DISPATCH_VIEWS) as DispatchViewKey[]).map((k) => (
          <Tabs.Content key={k} value={k} />
        ))}
      </Tabs.Root>

      {dp.err && (
        <CardError message={dp.err} onRetry={() => dp.fetchPage(dp.currentBefore)} />
      )}

      <DataTable
        columns={columns}
        rows={dp.rows}
        rowKey={(d) => d.dispatch_uuid}
        onRowClick={(d) => dp.openDetail(d.dispatch_uuid)}
        loading={dp.loading}
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
          onClick={dp.goPrev}
          disabled={dp.loading || dp.prevStack.length === 0}
        >
          ‹ Previous
        </Button>
        <span className="micro pager-status" aria-live="polite">
          Page {dp.pageIndex}
          {dp.rows.length > 0 &&
            ` · ${dp.rows.length} row${dp.rows.length === 1 ? "" : "s"}`}
        </span>
        <Button
          variant="neutral"
          size="sm"
          onClick={dp.goNext}
          disabled={dp.loading || !dp.nextCursor}
        >
          Next ›
        </Button>
      </nav>

      {(dp.detailLoading || dp.selected) && (
        <Card as="section" ref={dp.detailRef} style={{ marginTop: "var(--space-4)" }} aria-label="Dispatch detail">
          {dp.detailLoading && <Skeleton variant="card" />}
          {dp.selected && !dp.detailLoading && dp.journeyData && (
            <>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "var(--space-3)",
                }}
              >
                <span className="micro">
                  Dispatch <span className="mono">{dp.selected.dispatch_uuid}</span>
                </span>
                <Button variant="neutral" size="sm" onClick={() => dp.setSelected(null)}>
                  Close
                </Button>
              </div>
              <JourneyPanel data={dp.journeyData} />
            </>
          )}
        </Card>
      )}
    </div>
  );
}
