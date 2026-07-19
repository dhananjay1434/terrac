import styles from "./SealedVerdict.module.css";

export type Verdict = "ISSUABLE" | "PROVISIONAL" | "BLOCKED";

const VERDICT_COPY: Record<Verdict, string> = {
  ISSUABLE: "Verified & Sealed",
  PROVISIONAL: "Pending verification",
  BLOCKED: "Verification blocked",
};

/**
 * Notched-seal verdict badge colored by semantic token; non-issuable verdicts
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
    <div className={styles.wrap}>
      <span className={styles.stamp} data-verdict={verdict} data-size={size}>
        <svg
          className={styles.icon}
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          {verdict === "ISSUABLE" ? (
            <path
              d="M20 6 9 17l-5-5"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ) : (
            <path
              d="M12 8v5M12 16.5v.01M4 19h16L12 4 4 19Z"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}
        </svg>
        {verdict}
      </span>
      <div className={styles.caption}>
        {VERDICT_COPY[verdict]}
        {verdict !== "ISSUABLE" && reasonCount ? (
          <span className={styles.count}>
            {reasonCount} blocker{reasonCount === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
    </div>
  );
}
