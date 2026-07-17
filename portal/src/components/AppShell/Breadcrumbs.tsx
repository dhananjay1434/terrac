import { Link, useLocation } from "react-router-dom";
import type { ReactNode } from "react";
import styles from "./AppShell.module.css";

const LABELS: Record<string, string> = {
  "/batches": "Batches",
  "/lab/scan": "Lab / Scan",
  "/registry": "Registry",
};

/**
 * Location-derived breadcrumbs. Static map for fixed routes; dynamic routes
 * (/batches/:uuid, /lab/:uuid) show the parent label plus the short uuid.
 */
export default function Breadcrumbs() {
  const { pathname } = useLocation();
  let crumb: ReactNode = LABELS[pathname] ?? "";

  const batchMatch = pathname.match(/^\/batches\/(.+)$/);
  const labMatch = pathname.match(/^\/lab\/(.+)$/);
  if (batchMatch) {
    crumb = (
      <>
        <Link to="/batches">Batches</Link> /{" "}
        <span className="mono">{batchMatch[1].slice(0, 8)}</span>
      </>
    );
  } else if (labMatch && labMatch[1] !== "scan") {
    crumb = (
      <>
        Lab / <span className="mono">{labMatch[1].slice(0, 8)}</span>
      </>
    );
  }

  return <div className={styles.crumbs}>{crumb}</div>;
}
