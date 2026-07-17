import { fmtCredit } from "../../format";
import styles from "./LcaBreakdown.module.css";

/**
 * LCA summary. The API exposes only wet yield and the net credit today, so
 * this renders a simple list (a waterfall would require factor fields the
 * backend doesn't send — nothing is invented).
 */
export default function LcaBreakdown({
  wetYieldKg,
  netCreditTCo2e,
}: {
  wetYieldKg: number;
  netCreditTCo2e: number;
}) {
  return (
    <div className="card">
      <span className="micro">LCA summary</span>
      <ul className={styles.list}>
        <li className={styles.row}>
          <span className={styles.key}>Wet yield</span>
          <span className={`${styles.val} tabular`}>{wetYieldKg} kg</span>
        </li>
        <li className={styles.row}>
          <span className={styles.key}>Net credit</span>
          <span className={`${styles.val} tabular`}>
            {fmtCredit(netCreditTCo2e)} tCO₂e
          </span>
        </li>
      </ul>
      <div className={styles.note}>
        Full LCA factor breakdown is not exposed by the API yet.
      </div>
    </div>
  );
}
