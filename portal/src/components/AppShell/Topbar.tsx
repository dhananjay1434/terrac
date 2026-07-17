import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Menu, Sun, Moon, HelpCircle, CircleUser } from "lucide-react";
import { logout } from "../../api";
import { clearSession } from "../../auth";
import { getTheme, setTheme, type Theme } from "../../theme";
import styles from "./AppShell.module.css";

const RECENT_SCANS_KEY = "tc_recent_scans";

/**
 * Top bar: hamburger (mobile only), wordmark (collapsed rail or mobile),
 * theme toggle, help, and the account menu with Sign out — which reuses the
 * existing logout() + clearSession() pair exactly as the old TopBar did.
 * The account menu is a Radix DropdownMenu so outside-click, Escape, and
 * focus management come for free instead of being hand-rolled.
 */
export default function Topbar({
  collapsed,
  onOpenDrawer,
}: {
  collapsed: boolean;
  onOpenDrawer(): void;
}) {
  const nav = useNavigate();
  const [theme, setThemeState] = useState<Theme>(() => getTheme());
  const [signingOut, setSigningOut] = useState(false);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }

  async function signOut() {
    if (signingOut) return;
    setSigningOut(true);
    try {
      await logout();
    } finally {
      clearSession();
      // Cosmetic side-effect only — no auth/session-shape change: recent
      // lab scans are per-device convenience data, not audit state, and
      // shouldn't linger for the next person on a shared bench tablet.
      try {
        localStorage.removeItem(RECENT_SCANS_KEY);
      } catch {
        /* storage unavailable — non-fatal */
      }
      nav("/login");
    }
  }

  return (
    <header className={styles.topbar}>
      <button
        type="button"
        className={styles.hamburger}
        aria-label="Open navigation"
        onClick={onOpenDrawer}
      >
        <Menu size={18} aria-hidden />
      </button>
      <span
        className={styles.topbarWordmark}
        data-desktop-only={!collapsed}
      >
        TerraCipher
      </span>
      <div className={styles.topbarRight}>
        <button
          type="button"
          className={styles.iconBtn}
          aria-label={
            theme === "dark" ? "Switch to light theme" : "Switch to dark theme"
          }
          aria-pressed={theme === "dark"}
          onClick={toggleTheme}
        >
          {theme === "dark" ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
        </button>
        <button type="button" className={styles.iconBtn} aria-label="Help" title="Help">
          <HelpCircle size={16} aria-hidden />
        </button>
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button
              type="button"
              className={styles.iconBtn}
              aria-label="Account menu"
            >
              <CircleUser size={18} aria-hidden />
            </button>
          </DropdownMenu.Trigger>
          <DropdownMenu.Portal>
            <DropdownMenu.Content
              className={styles.menu}
              align="end"
              sideOffset={4}
            >
              <DropdownMenu.Item
                className={styles.menuItem}
                disabled={signingOut}
                onSelect={signOut}
              >
                {signingOut ? "Signing out…" : "Sign out"}
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  );
}
