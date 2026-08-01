import { fmtKg } from "../../format";
import StatusPill from "../../ui/StatusPill/StatusPill";
import DataTable, { type ColumnDef } from "../DataTable/DataTable";
import MetricBlock from "../MetricBlock/MetricBlock";
import styles from "./JourneyPanel.module.css";

/**
 * Dispatch journey detail panel (M4.4). Renders journey metrics, cargo
 * manifest, (already-masked) recipient contact, emissions, and application-
 * evidence status for a dispatch. The route map is a stitch slot (Leaflet via
 * the shared ParcelMap plugs in during the M4 wiring — kept out here so this
 * ships from the parallel lane without touching a shared component).
 *
 * Surfaces audit A7 in the UI: a manually-entered distance is chipped as such
 * so a reviewer can see it could only have RAISED the transport deduction,
 * never lowered the credit; a GPS-traced distance is chipped "GPS-traced".
 * Missing values render as em-dash — never fabricated.
 */
import ParcelMap from "../ParcelMap/ParcelMap";

export interface JourneyManifestLine {
  container: string;
  count: number;
  unit_kg?: number | null;
  volume_l?: number | null;
  product: string;
}
export interface JourneyData {
  distance_km: number | null;
  distance_source: "gps" | "manual" | null;
  vehicle_reg: string | null;
  fuel_type: string | null;
  emissions_kg: number | null;
  factor_version: string | null;
  recipient?: { contact_name: string | null; contact_phone_masked: string | null } | null;
  manifest?: JourneyManifestLine[];
  application_evidence?: { count: number } | null;
  route_geojson?: Record<string, unknown> | null;
}

const DASH = "—";

function km(v: number | null): string {
  return v == null ? DASH : `${v.toFixed(1)} km`;
}
function co2(v: number | null): string {
  return v == null ? DASH : `${v.toLocaleString(undefined, { maximumFractionDigits: 1 })} kgCO₂e`;
}

export default function JourneyPanel({ data }: { data: JourneyData }) {
  const rows: { label: string; value: React.ReactNode }[] = [
    {
      label: "Distance",
      value: (
        <span className={styles.distanceCell}>
          <span className="mono tabular">{km(data.distance_km)}</span>
          {data.distance_source === "gps" && <StatusPill status="success">GPS-traced</StatusPill>}
          {data.distance_source === "manual" && (
            <span className={styles.manualChip}>manually entered</span>
          )}
        </span>
      ),
    },
    { label: "Vehicle", value: <span className="mono">{data.vehicle_reg ?? DASH}</span> },
    { label: "Fuel", value: data.fuel_type ?? DASH },
    {
      label: "Est. emissions",
      value: (
        <span>
          <span className="mono tabular">{co2(data.emissions_kg)}</span>
          {data.factor_version && <span className={styles.factor}> · {data.factor_version}</span>}
        </span>
      ),
    },
  ];

  const manifest = data.manifest ?? [];
  const appCount = data.application_evidence?.count ?? 0;
  const manifestMassKg = manifest.reduce(
    (sum, m) => sum + (m.unit_kg != null ? m.unit_kg * m.count : 0),
    0,
  );
  const manifestHasMass = manifest.some((m) => m.unit_kg != null);

  return (
    <section className={styles.panel} aria-label="Journey details">
      <div className={styles.head}>
        <span className="micro">Distribution details</span>
      </div>

      <dl className={styles.metrics}>
        {rows.map((r) => (
          <div key={r.label} className={styles.metric}>
            <dt className="micro">{r.label}</dt>
            <dd>{r.value}</dd>
          </div>
        ))}
      </dl>

      {data.recipient && (
        <div className={styles.recipient}>
          <span className="micro">Recipient</span>
          <span>
            {data.recipient.contact_name ?? DASH}
            {data.recipient.contact_phone_masked && (
              <span className="mono"> · {data.recipient.contact_phone_masked}</span>
            )}
          </span>
        </div>
      )}

      <div className={styles.manifest}>
        <span className="micro">Cargo manifest</span>
        {manifestHasMass && (
          <MetricBlock value={fmtKg(manifestMassKg).replace(/\s*kg$/, "")} unit="kg" caption="total cargo mass" size="md" />
        )}
        {manifest.length === 0 ? (
          <div className="text-tertiary">{DASH} no manifest lines</div>
        ) : (
          <DataTable<JourneyManifestLine>
            columns={manifestColumns}
            rows={manifest}
            rowKey={(m) => `${m.container}-${manifest.indexOf(m)}`}
          />
        )}
      </div>

      <div className={styles.appEvidence}>
        <span className="micro">Application evidence</span>
        {appCount > 0 ? (
          <StatusPill status="success">{appCount} record{appCount === 1 ? "" : "s"}</StatusPill>
        ) : (
          <StatusPill status="warning">not started</StatusPill>
        )}
      </div>

      {/* M4 stitch slot: Leaflet route polyline (route_geojson) mounts here via
          the shared ParcelMap/MapCanvas — deferred to keep this parallel-safe. */}
      {data.route_geojson ? (
        <div className={styles.routeSlot}>
          <span className="micro">Route map</span>
          <div style={{ height: "300px", marginTop: "var(--space-2)" }}>
            <ParcelMap selectedGeoJson={data.route_geojson} readOnly={true} />
          </div>
        </div>
      ) : (
        <div className={styles.routeSlot} data-testid="route-slot" aria-hidden />
      )}
    </section>
  );
}

const manifestColumns: ColumnDef<JourneyManifestLine>[] = [
  { key: "container", header: "Container", render: (m) => m.container },
  { key: "count", header: "Count", align: "right", mono: true, render: (m) => m.count },
  {
    key: "mass",
    header: "Mass / volume",
    align: "right",
    mono: true,
    render: (m) =>
      m.unit_kg != null
        ? fmtKg(m.unit_kg * m.count)
        : m.volume_l != null
          ? `${(m.volume_l * m.count).toLocaleString()} L`
          : DASH,
  },
  { key: "product", header: "Product", render: (m) => m.product },
];
