import React, { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  createProject,
  listProjects,
  createParcel,
  listParcels,
  AuthError,
  ApiError,
  type ProjectRow,
  type SourceParcel,
} from "../api";
import DataTable, { type ColumnDef } from "../components/DataTable/DataTable";
import EmptyState from "../components/EmptyState/EmptyState";
import ParcelMap from "../components/ParcelMap/ParcelMap";

const PAGE_SIZE = 25;

function fmtDate(iso: string | null) {
  return iso ? iso.slice(0, 10) : "—";
}

export default function Projects() {
  const nav = useNavigate();
  const [rows, setRows] = useState<ProjectRow[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [currentBefore, setCurrentBefore] = useState<string | null>(null);
  const [prevStack, setPrevStack] = useState<(string | null)[]>([]);
  const [pageIndex, setPageIndex] = useState(1);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // Project form state
  const [projectId, setProjectId] = useState("");
  const [name, setName] = useState("");
  const [formMsg, setFormMsg] = useState<{ text: string; ok: boolean } | null>(
    null,
  );
  const [submitting, setSubmitting] = useState(false);

  // Parcel form & list state (Part 1.5)
  const [parcels, setParcels] = useState<SourceParcel[]>([]);
  const [parcelsLoading, setParcelsLoading] = useState(false);
  const [parcelProjectId, setParcelProjectId] = useState("");
  const [parcelName, setParcelName] = useState("");
  const [declaredAcres, setDeclaredAcres] = useState("");
  const [drawnGeoJson, setDrawnGeoJson] = useState<Record<string, unknown> | null>(null);
  const [parcelMsg, setParcelMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [parcelSubmitting, setParcelSubmitting] = useState(false);

  const fetchPage = useCallback(
    async (before: string | null) => {
      setLoading(true);
      setErr(null);
      try {
        const params: Record<string, string> = { limit: String(PAGE_SIZE) };
        if (before) params.before = before;
        const r = await listProjects(params);
        setRows(r.projects);
        setNextCursor(r.next_cursor);
        if (r.projects.length > 0 && !parcelProjectId) {
          setParcelProjectId(r.projects[0].project_id);
        }
      } catch (e) {
        if (e instanceof AuthError) nav("/login");
        else setErr("Failed to load projects.");
      } finally {
        setLoading(false);
      }
    },
    [nav, parcelProjectId],
  );

  const fetchParcels = useCallback(async () => {
    setParcelsLoading(true);
    try {
      const res = await listParcels(parcelProjectId || undefined);
      setParcels(res.parcels);
    } catch (_) {
      /* ignore parcel load failure in background */
    } finally {
      setParcelsLoading(false);
    }
  }, [parcelProjectId]);

  useEffect(() => {
    document.title = "Projects · TerraCipher";
    fetchPage(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchParcels();
  }, [fetchParcels, parcelProjectId]);

  useEffect(() => {
    if (!formMsg) return;
    const t = setTimeout(() => setFormMsg(null), 4000);
    return () => clearTimeout(t);
  }, [formMsg]);

  useEffect(() => {
    if (!parcelMsg) return;
    const t = setTimeout(() => setParcelMsg(null), 5000);
    return () => clearTimeout(t);
  }, [parcelMsg]);

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

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!projectId.trim() || !name.trim()) {
      setFormMsg({ text: "Project ID and name are required", ok: false });
      return;
    }
    setSubmitting(true);
    setFormMsg(null);
    try {
      await createProject({ project_id: projectId.trim(), name: name.trim() });
      setFormMsg({ text: "✓ Project created", ok: true });
      setProjectId("");
      setName("");
      setPrevStack([]);
      setCurrentBefore(null);
      setPageIndex(1);
      await fetchPage(null);
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError && e.status === 409) {
        setFormMsg({ text: "A project with that ID already exists", ok: false });
      } else {
        setFormMsg({ text: "Create failed — check values", ok: false });
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function submitParcel(e: React.FormEvent) {
    e.preventDefault();
    if (!parcelProjectId.trim() || !parcelName.trim() || !drawnGeoJson) {
      setParcelMsg({ text: "Project ID, Parcel Name, and Boundary GeoJSON are required", ok: false });
      return;
    }
    setParcelSubmitting(true);
    setParcelMsg(null);
    try {
      const acres = declaredAcres.trim() ? parseFloat(declaredAcres.trim()) : undefined;
      await createParcel({
        project_id: parcelProjectId.trim(),
        name: parcelName.trim(),
        boundary_geojson: drawnGeoJson,
        declared_area_acres: acres,
      });
      setParcelMsg({ text: "✓ Source parcel boundary registered & approved", ok: true });
      setParcelName("");
      setDeclaredAcres("");
      setDrawnGeoJson(null);
      await fetchParcels();
    } catch (e) {
      if (e instanceof AuthError) {
        nav("/login");
      } else if (e instanceof ApiError) {
        let msg = e.message;
        try {
          const detailObj = JSON.parse(e.message);
          if (detailObj.message) msg = detailObj.message;
        } catch (_) {}
        setParcelMsg({ text: `Parcel registration failed: ${msg}`, ok: false });
      } else {
        setParcelMsg({ text: "Parcel registration failed", ok: false });
      }
    } finally {
      setParcelSubmitting(false);
    }
  }

  const columns: ColumnDef<ProjectRow>[] = [
    { key: "project_id", header: "Project ID", mono: true, render: (p) => p.project_id },
    { key: "name", header: "Name", render: (p) => p.name },
    { key: "status", header: "Status", render: (p) => p.status },
    { key: "created", header: "Created", render: (p) => fmtDate(p.created_at) },
  ];

  const parcelColumns: ColumnDef<SourceParcel>[] = [
    { key: "parcel_uuid", header: "Parcel UUID", mono: true, render: (p) => p.parcel_uuid.slice(0, 8) + "..." },
    { key: "name", header: "Parcel Name", render: (p) => p.name },
    { key: "project_id", header: "Project ID", mono: true, render: (p) => p.project_id },
    { key: "area", header: "Area (m²)", render: (p) => `${p.area_m2.toLocaleString()} m²` },
    { key: "acres", header: "Declared (Acres)", render: (p) => p.declared_area_acres ? `${p.declared_area_acres} acres` : "—" },
    { key: "status", header: "Status", render: (p) => p.boundary_status },
    { key: "created", header: "Created", render: (p) => fmtDate(p.created_at) },
  ];

  return (
    <div className="wrap">
      <h1 className="page-title">Projects & Source Parcels</h1>

      {/* Project Registration Form */}
      <form className="card" style={{ marginBottom: 20 }} onSubmit={submit}>
        <span className="micro">Register project</span>
        <div className="filters" style={{ marginTop: 10 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="project-id-input">
              Project ID
            </label>
            <input
              id="project-id-input"
              aria-label="Project ID"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="project-name-input">
              Name
            </label>
            <input
              id="project-name-input"
              aria-label="Project name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <button
            className="primary"
            type="submit"
            disabled={submitting}
            style={{ alignSelf: "flex-end" }}
          >
            Save
          </button>
        </div>
        {formMsg && (
          <div style={{ marginTop: 12 }}>
            <div className={`chip ${formMsg.ok ? "ok" : "err"}`}>{formMsg.text}</div>
          </div>
        )}
      </form>

      {/* Source Parcel Boundary Registration Form (Part 1.5) */}
      <form className="card" style={{ marginBottom: 20 }} onSubmit={submitParcel}>
        <span className="micro">Register Source Parcel Boundary (Leaflet / OSM)</span>
        <div className="filters" style={{ marginTop: 10, marginBottom: 12 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="parcel-project-select">
              Select Project
            </label>
            <select
              id="parcel-project-select"
              aria-label="Select Project"
              value={parcelProjectId}
              onChange={(e) => setParcelProjectId(e.target.value)}
            >
              <option value="">-- Choose Project --</option>
              {rows.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name} ({p.project_id})
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="parcel-name-input">
              Parcel Name
            </label>
            <input
              id="parcel-name-input"
              aria-label="Parcel Name"
              value={parcelName}
              placeholder="e.g. North Harvest Parcel A"
              onChange={(e) => setParcelName(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label className="micro" htmlFor="declared-acres-input">
              Declared Acres (Optional)
            </label>
            <input
              id="declared-acres-input"
              aria-label="Declared Acres"
              type="number"
              step="any"
              value={declaredAcres}
              placeholder="e.g. 5.5"
              onChange={(e) => setDeclaredAcres(e.target.value)}
            />
          </div>
        </div>

        <ParcelMap
          existingParcels={parcels}
          onPolygonCreated={(geojson) => setDrawnGeoJson(geojson)}
          selectedGeoJson={drawnGeoJson}
        />

        <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
          <button
            className="primary"
            type="submit"
            disabled={parcelSubmitting || !drawnGeoJson}
          >
            Register Boundary
          </button>
        </div>

        {parcelMsg && (
          <div style={{ marginTop: 12 }}>
            <div className={`chip ${parcelMsg.ok ? "ok" : "err"}`}>{parcelMsg.text}</div>
          </div>
        )}
      </form>

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

      {/* Projects Table */}
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Registered Projects</h2>
      <DataTable
        columns={columns}
        rows={rows}
        rowKey={(p) => p.project_id}
        loading={loading}
        empty={
          <EmptyState
            title="No projects yet"
            description="Register a project above — batches synced from the field can then resolve it by their project_id."
          />
        }
      />

      <nav className="pager" aria-label="Projects pagination" style={{ marginBottom: 24 }}>
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

      {/* Source Parcels Table */}
      <h2 style={{ fontSize: 16, marginBottom: 8 }}>Source Parcels</h2>
      <DataTable
        columns={parcelColumns}
        rows={parcels}
        rowKey={(p) => p.parcel_uuid}
        loading={parcelsLoading}
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
