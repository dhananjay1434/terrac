import type { FormEvent } from "react";
import type { ProjectRow, SourceParcel } from "../../api";
import ParcelMap from "../../components/ParcelMap/ParcelMap";
import Button from "../../ui/Button/Button";
import Card from "../../ui/Card/Card";
import StatusPill from "../../ui/StatusPill/StatusPill";

export interface ParcelFormProps {
  projects: ProjectRow[];
  parcelProjectId: string;
  onParcelProjectIdChange: (v: string) => void;
  parcelName: string;
  onParcelNameChange: (v: string) => void;
  declaredAcres: string;
  onDeclaredAcresChange: (v: string) => void;
  existingParcels: SourceParcel[];
  drawnGeoJson: Record<string, unknown> | null;
  onPolygonCreated: (geojson: Record<string, unknown>) => void;
  parcelSubmitting: boolean;
  parcelMsg: { text: string; ok: boolean } | null;
  onSubmit: (e: FormEvent) => void;
}

/** Presentational-only: the "Register Source Parcel Boundary" form section.
 * All state and submit logic live in the Projects page. The map itself
 * (ParcelMap and its props) is passed through untouched. */
export default function ParcelForm({
  projects,
  parcelProjectId,
  onParcelProjectIdChange,
  parcelName,
  onParcelNameChange,
  declaredAcres,
  onDeclaredAcresChange,
  existingParcels,
  drawnGeoJson,
  onPolygonCreated,
  parcelSubmitting,
  parcelMsg,
  onSubmit,
}: ParcelFormProps) {
  return (
    <Card as="form" style={{ marginBottom: 20 }} onSubmit={onSubmit}>
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
            onChange={(e) => onParcelProjectIdChange(e.target.value)}
          >
            <option value="">-- Choose Project --</option>
            {projects.map((p) => (
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
            onChange={(e) => onParcelNameChange(e.target.value)}
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
            onChange={(e) => onDeclaredAcresChange(e.target.value)}
          />
        </div>
      </div>

      <ParcelMap
        existingParcels={existingParcels}
        onPolygonCreated={onPolygonCreated}
        selectedGeoJson={drawnGeoJson}
      />

      <div style={{ marginTop: 12, display: "flex", justifyContent: "flex-end" }}>
        <Button type="submit" disabled={parcelSubmitting || !drawnGeoJson}>
          Register Boundary
        </Button>
      </div>

      {parcelMsg && (
        <div style={{ marginTop: 12 }}>
          <StatusPill status={parcelMsg.ok ? "success" : "error"}>{parcelMsg.text}</StatusPill>
        </div>
      )}
    </Card>
  );
}
