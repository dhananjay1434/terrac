import { fmtKg } from "../../format";
import StatusPill from "../../ui/StatusPill/StatusPill";
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
        {manifest.length === 0 ? (
          <div className="text-tertiary">{DASH} no manifest lines</div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Container</th>
                <th className={styles.num}>Count</th>
                <th className={styles.num}>Mass / volume</th>
                <th>Product</th>
              </tr>
            </thead>
            <tbody>
              {manifest.map((m, i) => (
                <tr key={i}>
                  <td>{m.container}</td>
                  <td className={`${styles.num} mono tabular`}>{m.count}</td>
                  <td className={`${styles.num} mono tabular`}>
                    {m.unit_kg != null
                      ? fmtKg(m.unit_kg * m.count)
                      : m.volume_l != null
                        ? `${(m.volume_l * m.count).toLocaleString()} L`
                        : DASH}
                  </td>
                  <td>{m.product}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
      <div className={styles.routeSlot} data-testid="route-slot" aria-hidden />
    </section>
  );
}
