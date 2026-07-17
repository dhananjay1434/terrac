import { Link, useLocation } from "react-router-dom";
import {
  Layers,
  FlaskConical,
  Archive,
  Settings,
  HelpCircle,
  PanelLeft,
  PanelLeftClose,
} from "lucide-react";
import clsx from "clsx";
import styles from "./AppShell.module.css";

const NAV = [
  { to: "/batches", label: "Batches", match: "/batches", Icon: Layers },
  { to: "/lab/scan", label: "Lab", match: "/lab", Icon: FlaskConical },
  { to: "/registry", label: "Registry", match: "/registry", Icon: Archive },
];

/**
 * Left navigation rail: logo lockup, primary nav (active state from the
 * current location), footer utilities, and the collapse toggle. Collapsed
 * state is owned by AppShell and persisted there.
 */
export default function Sidebar({
  collapsed,
  onToggle,
  drawerOpen = false,
  onNavigate,
}: {
  collapsed: boolean;
  onToggle(): void;
  drawerOpen?: boolean;
  onNavigate?(): void;
}) {
  const { pathname } = useLocation();
  return (
    <aside
      className={styles.rail}
      data-collapsed={collapsed}
      data-drawer-open={drawerOpen}
      aria-label="Primary"
    >
      <div className={styles.lockup}>
        <div className={styles.mark}>TC</div>
        {!collapsed && <span className={styles.wordmark}>TerraCipher</span>}
      </div>
      <nav className={styles.nav} aria-label="Primary navigation">
        {NAV.map(({ to, label, match, Icon }) => {
          const active = pathname.startsWith(match);
          return (
            <Link
              key={to}
              to={to}
              className={clsx(styles.navItem, active && styles.navItemActive)}
              aria-current={active ? "page" : undefined}
              aria-label={label}
              title={collapsed ? label : undefined}
              onClick={onNavigate}
            >
              <Icon size={16} aria-hidden />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </nav>
      <div className={styles.railFooter}>
        <button className={styles.navItem} type="button" disabled title="Settings (coming soon)">
          <Settings size={16} aria-hidden />
          {!collapsed && <span>Settings</span>}
        </button>
        <button className={styles.navItem} type="button" title="Help">
          <HelpCircle size={16} aria-hidden />
          {!collapsed && <span>Help</span>}
        </button>
        <button
          className={styles.navItem}
          type="button"
          onClick={onToggle}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title="⌘\"
        >
          {collapsed ? (
            <PanelLeft size={16} aria-hidden />
          ) : (
            <PanelLeftClose size={16} aria-hidden />
          )}
          {!collapsed && <span>Collapse</span>}
        </button>
      </div>
    </aside>
  );
}
