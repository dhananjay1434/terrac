import { useCallback, useEffect, useState, type ReactNode } from "react";
import { useLocation } from "react-router-dom";
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
  const { pathname } = useLocation();
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(COLLAPSE_KEY) === "true",
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

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
      if (e.key === "Escape") setDrawerOpen(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [toggle]);

  // Close the mobile drawer whenever the route changes, so navigating from
  // it doesn't leave it open over the new page.
  useEffect(() => {
    setDrawerOpen(false);
  }, [pathname]);

  return (
    <div className={styles.shell}>
      <a href="#main-content" className={styles.skip}>
        Skip to content
      </a>
      <EnvBanner />
      <div className={styles.row}>
        <div
          className={styles.scrim}
          data-open={drawerOpen}
          onClick={() => setDrawerOpen(false)}
          aria-hidden
        />
        <Sidebar
          collapsed={collapsed}
          onToggle={toggle}
          drawerOpen={drawerOpen}
          onNavigate={() => setDrawerOpen(false)}
        />
        <div className={styles.body}>
          <Topbar collapsed={collapsed} onOpenDrawer={() => setDrawerOpen(true)} />
          <Breadcrumbs />
          <main id="main-content" tabIndex={-1} className={styles.main}>
            {children}
          </main>
        </div>
      </div>
    </div>
  );
}
