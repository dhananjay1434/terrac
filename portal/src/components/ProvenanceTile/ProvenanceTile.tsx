import CopyButton from "../CopyButton/CopyButton";
import styles from "./ProvenanceTile.module.css";

/**
 * Chain-of-custody facts for a batch. Renders ONLY fields the API exposes on
 * BatchDetail today; anything the backend doesn't send (methodology version)
 * is an em-dash — never fabricated.
 */
export default function ProvenanceTile({
  batchUuid,
  deviceId,
  projectId,
  receivedAt,
}: {
  batchUuid: string;
  deviceId: string | null;
  projectId: string | null;
  receivedAt: string | null;
}) {
  const rows: [string, React.ReactNode][] = [
    [
      "Batch ID",
      <span key="id" className="mono">
        {batchUuid.slice(0, 8)}… <CopyButton value={batchUuid} label="Copy batch id" />
      </span>,
    ],
    ["Device", deviceId ?? "—"],
    ["Project", projectId ?? "—"],
    [
      "Received",
      receivedAt ? (
        <span className="tabular">
          {receivedAt.slice(0, 16).replace("T", " ")}
        </span>
      ) : (
        "—"
      ),
    ],
    ["Methodology", "—"],
  ];
  return (
    <div className="card">
      <span className="micro">Provenance</span>
      <dl className={styles.list}>
        {rows.map(([k, v]) => (
          <div key={k} className={styles.row}>
            <dt className={styles.key}>{k}</dt>
            <dd className={styles.val}>{v}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
