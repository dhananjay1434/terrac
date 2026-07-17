import { useCallback, useEffect, useState, type ReactNode } from "react";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import Breadcrumbs from "./Breadcrumbs";
import EnvBanner from "./EnvBanner";
import styles from "./AppShell.module.css";

const COLLAPSE_KEY = "tc_rail_collapsed";

/**
 * Application chrome for authed screens: env banner on top, left rail,
 * topbar + breadcrumbs above the page content. Owns the rail collapsed
 * state (persisted to localStorage, toggled by button or ⌘\ / Ctrl+\).
 * Purely presentational — routing, auth, and data flow are untouched.
 */
export default function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === "true",
  );

  const toggle = useCallback(() => {
    setCollapsed((c) => {
      localStorage.setItem(COLLAPSE_KEY, String(!c));
      return !c;
    });
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "\\" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        toggle();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  return (
    <div className={styles.shell}>
      <EnvBanner />
      <div className={styles.row}>
        <Sidebar collapsed={collapsed} onToggle={toggle} />
        <div className={styles.body}>
          <Topbar collapsed={collapsed} onCmdK={() => {}} />
          <Breadcrumbs />
          <main className={styles.main}>{children}</main>
        </div>
      </div>
    </div>
  );
}
