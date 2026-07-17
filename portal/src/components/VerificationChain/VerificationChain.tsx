import styles from "./VerificationChain.module.css";

export interface ChainNode {
  label: string;
  sublabel?: string;
  state: "done" | "current" | "pending" | "failed";
}

/**
 * Horizontal chain-of-custody strip (stacks vertically on narrow screens).
 * Each node shows a state marker, label, and optional sublabel; states map
 * to semantic tokens only.
 */
export default function VerificationChain({ nodes }: { nodes: ChainNode[] }) {
  return (
    <ol className={styles.chain} aria-label="Verification chain">
      {nodes.map((n, i) => (
        <li key={n.label} className={styles.node} data-state={n.state}>
          <span className={styles.marker} aria-hidden>
            {n.state === "done" ? "✓" : n.state === "failed" ? "✕" : i + 1}
          </span>
          <span className={styles.labels}>
            <span className={styles.label}>{n.label}</span>
            {n.sublabel && <span className={styles.sub}>{n.sublabel}</span>}
          </span>
          {i < nodes.length - 1 && (
            <span className={styles.connector} aria-hidden />
          )}
        </li>
      ))}
    </ol>
  );
}
