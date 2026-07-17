import styles from "./SealedVerdict.module.css";

export type Verdict = "ISSUABLE" | "PROVISIONAL" | "BLOCKED";

/**
 * Stamp-style verdict badge colored by semantic token; non-issuable verdicts
 * show the blocker count so color is never the sole signal.
 */
export default function SealedVerdict({
  verdict,
  reasonCount,
  size = "md",
}: {
  verdict: Verdict;
  reasonCount?: number;
  size?: "md" | "lg";
}) {
  return (
    <span
      className={styles.stamp}
      data-verdict={verdict}
      data-size={size}
    >
      {verdict}
      {verdict !== "ISSUABLE" && reasonCount ? (
        <span className={styles.count}>
          {reasonCount} blocker{reasonCount === 1 ? "" : "s"}
        </span>
      ) : null}
    </span>
  );
}
