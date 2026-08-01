import type { ProjectRow, SourceParcel } from "../api";
import { fmtDate } from "../format";
import { getRole } from "../auth";
import StatusDot, { type StatusDotVariant } from "../components/StatusDot/StatusDot";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import EmptyState from "../components/EmptyState/EmptyState";
import Button from "../ui/Button/Button";
import CardError from "../ui/CardError/CardError";
import ProjectForm from "./Projects/ProjectForm";
import ParcelForm from "./Projects/ParcelForm";
import { useProjects } from "../features/projects/useProjects";

const projectStatusVariant = (s: string): StatusDotVariant =>
  s === "active" || s === "verified"
    ? "success"
    : s === "draft" || s === "provisional"
      ? "warning"
      : "inert";

const columns: ColumnDef<ProjectRow>[] = [
  { key: "project_id", header: "Project ID", mono: true, render: (p) => p.project_id },
  { key: "name", header: "Name", render: (p) => p.name },
  {
    key: "feedstock",
    header: "Feedstock",
    render: (p) => (p.allowed_feedstocks.length > 0 ? p.allowed_feedstocks.join(", ") : "—"),
  },
  {
    key: "clients",
    header: "Clients",
    render: (p) => (p.client_target != null ? String(p.client_target) : "—"),
  },
  {
    key: "status",
    header: "Status",
    render: (p) => <StatusDot variant={projectStatusVariant(p.status)} label={p.status} />,
  },
  { key: "created", header: "Created", render: (p) => fmtDate(p.created_at) },
];

const parcelColumns: ColumnDef<SourceParcel>[] = [
  { key: "parcel_uuid", header: "Parcel UUID", mono: true, render: (p) => p.parcel_uuid.slice(0, 8) + "…" },
  { key: "name", header: "Parcel name", render: (p) => p.name },
  { key: "project_id", header: "Project ID", mono: true, render: (p) => p.project_id },
  { key: "area", header: "Area (m²)", render: (p) => `${p.area_m2.toLocaleString()} m²` },
  { key: "acres", header: "Declared (acres)", render: (p) => p.declared_area_acres ? `${p.declared_area_acres} acres` : "—" },
  {
    key: "status",
    header: "Status",
    render: (p) =>
      p.boundary_status ? (
        <StatusDot variant={projectStatusVariant(p.boundary_status)} label={p.boundary_status} />
      ) : (
        "—"
      ),
  },
  { key: "created", header: "Created", render: (p) => fmtDate(p.created_at) },
];

export default function Projects() {
  const pr = useProjects();
  const isAdmin = getRole() === "admin";

  return (
    <div className="wrap">
      <h1 className="page-title">Projects & source parcels</h1>

      {/* Project & parcel registration is admin-only — verifiers read the
          tables below but never see write controls they can't authorize. */}
      {isAdmin && (
        <ProjectForm
          projectId={pr.projectId}
          onProjectIdChange={pr.setProjectId}
          name={pr.name}
          onNameChange={pr.setName}
          feedstockOptions={pr.feedstockOptions}
          selectedFeedstock={pr.selectedFeedstock}
          onFeedstockChange={pr.setSelectedFeedstock}
          clientTarget={pr.clientTarget}
          onClientTargetChange={pr.setClientTarget}
          submitting={pr.submitting}
          formMsg={pr.formMsg}
          onSubmit={pr.submit}
        />
      )}

      {/* Source Parcel Boundary Registration Form (Part 1.5) */}
      {isAdmin && (
        <ParcelForm
          projects={pr.rows}
          parcelProjectId={pr.parcelProjectId}
          onParcelProjectIdChange={pr.setParcelProjectId}
          parcelName={pr.parcelName}
          onParcelNameChange={pr.setParcelName}
          declaredAcres={pr.declaredAcres}
          onDeclaredAcresChange={pr.setDeclaredAcres}
          existingParcels={pr.parcels}
          drawnGeoJson={pr.drawnGeoJson}
          onPolygonCreated={(geojson) => pr.setDrawnGeoJson(geojson)}
          parcelSubmitting={pr.parcelSubmitting}
          parcelMsg={pr.parcelMsg}
          onSubmit={pr.submitParcel}
        />
      )}

      {pr.err && (
        <CardError message={pr.err} onRetry={() => pr.fetchPage(pr.currentBefore)} />
      )}

      {/* Projects Table */}
      <h2 className="section-title">Registered projects</h2>
      <DataTable
        columns={columns}
        rows={pr.rows}
        rowKey={(p) => p.project_id}
        loading={pr.loading}
        empty={
          <EmptyState
            title="No projects yet"
            description="Register a project above — batches synced from the field can then resolve it by their project_id."
          />
        }
      />

      <nav className="pager" aria-label="Projects pagination" style={{ marginBottom: "var(--space-5)" }}>
        <Button
          variant="neutral"
          size="sm"
          onClick={pr.goPrev}
          disabled={pr.loading || pr.prevStack.length === 0}
        >
          ‹ Previous
        </Button>
        <span className="micro pager-status" aria-live="polite">
          Page {pr.pageIndex}
          {pr.rows.length > 0 &&
            ` · ${pr.rows.length} row${pr.rows.length === 1 ? "" : "s"}`}
        </span>
        <Button
          variant="neutral"
          size="sm"
          onClick={pr.goNext}
          disabled={pr.loading || !pr.nextCursor}
        >
          Next ›
        </Button>
      </nav>

      {/* Source Parcels Table */}
      <h2 className="section-title">Source parcels</h2>
      <DataTable
        columns={parcelColumns}
        rows={pr.parcels}
        rowKey={(p) => p.parcel_uuid}
        loading={pr.parcelsLoading}
        empty={
          <EmptyState
            title="No source parcels registered"
            description="Draw or paste a boundary polygon above to register a source parcel for your project."
          />
        }
      />
    </div>
  );
}
