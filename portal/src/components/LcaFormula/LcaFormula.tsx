import type { LcaBreakdown } from "../../api";
import { fmtCredit } from "../../format";
import styles from "./LcaFormula.module.css";

const CO2_PER_C = 44 / 12;

/**
 * The annotated CSI credit formula (our real methodology, not a generic
 * template): Net credit = carbon remaining × 44/12 − safety − transport −
 * pyrolysis (CH4), all reconciled to one unit (tCO2e). `gross_c_sink_t_co2e`
 * is shown separately and labeled informational — it's a pre-decay figure,
 * never the issued credit (see lca_engine.py's own "informational only, not
 * used in issuance" note).
 */
export default function LcaFormula({
  breakdown,
}: {
  breakdown: LcaBreakdown | null | undefined;
}) {
  // Missing breakdown, or a breakdown missing the two fields the formula
  // needs, both render as "pending" — never a NaN/undefined in the UI.
  if (
    !breakdown ||
    breakdown.net_credit_t_co2e === undefined ||
    breakdown.cremain_t === undefined
  ) {
    return (
      <div className="card">
        <span className="micro">Credit formula</span>
        <div className={styles.pending}>Credit breakdown pending</div>
      </div>
    );
  }

  const term1 = breakdown.cremain_t * CO2_PER_C;
  const dSafety = (breakdown.safety_deduction_kg ?? 0) / 1000;
  const dTransport = (breakdown.transport_penalty_kg ?? 0) / 1000;
  const dCh4 = (breakdown.ch4_penalty_kg ?? 0) / 1000;
  const net = breakdown.net_credit_t_co2e;

  return (
    <div className="card">
      <span className="micro">Credit formula</span>
      {breakdown.provisional && (
        <div className={styles.provisional}>Provisional — not yet issued</div>
      )}
      <ul className={styles.list}>
        <li className={styles.row}>
          <span className={styles.key}>Carbon remaining</span>
          <span className={`${styles.val} tabular`}>{fmtCredit(term1)} tCO₂e</span>
        </li>
        <li className={styles.row}>
          <span className={styles.key}>− Safety margin</span>
          <span className={`${styles.val} tabular`}>{fmtCredit(dSafety)} tCO₂e</span>
        </li>
        <li className={styles.row}>
          <span className={styles.key}>− Transport</span>
          <span className={`${styles.val} tabular`}>{fmtCredit(dTransport)} tCO₂e</span>
        </li>
        <li className={styles.row}>
          <span className={styles.key}>− Pyrolysis (CH₄)</span>
          <span className={`${styles.val} tabular`}>{fmtCredit(dCh4)} tCO₂e</span>
        </li>
      </ul>
      <div className={styles.net}>
        <span className={styles.key}>= Net credit</span>
        <span className={`${styles.netVal} tabular`}>{fmtCredit(net)} tCO₂e</span>
      </div>
      {breakdown.gross_c_sink_t_co2e !== undefined && (
        <div className={styles.informational}>
          Informational (gross, pre-deduction) — not the issued credit:{" "}
          {fmtCredit(breakdown.gross_c_sink_t_co2e)} tCO₂e
        </div>
      )}
    </div>
  );
}
