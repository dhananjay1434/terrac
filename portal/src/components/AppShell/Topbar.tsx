import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search, Sun, Moon, HelpCircle, CircleUser } from "lucide-react";
import { logout } from "../../api";
import { clearSession } from "../../auth";
import { getTheme, setTheme, type Theme } from "../../theme";
import styles from "./AppShell.module.css";

/**
 * Top bar: wordmark (only when the rail is collapsed), search placeholder
 * (wired to the command palette in a later phase), theme toggle, help, and
 * the account menu with Sign out — which reuses the existing logout() +
 * clearSession() pair exactly as the old TopBar did.
 */
export default function Topbar({
  onCmdK,
  collapsed,
}: {
  onCmdK(): void;
  collapsed: boolean;
}) {
  const nav = useNavigate();
  const [theme, setThemeState] = useState<Theme>(() => getTheme());
  const [menuOpen, setMenuOpen] = useState(false);

  function toggleTheme() {
    const next: Theme = theme === "dark" ? "light" : "dark";
    setTheme(next);
    setThemeState(next);
  }

  async function signOut() {
    await logout();
    clearSession();
    nav("/login");
  }

  return (
    <header className={styles.topbar}>
      {collapsed && <span className={styles.topbarWordmark}>TerraCipher</span>}
      <button className={styles.search} type="button" onClick={onCmdK}>
        <Search size={14} aria-hidden />
        <span>Search…</span>
        <kbd>⌘K</kbd>
      </button>
      <div className={styles.topbarRight}>
        <button
          type="button"
          className={styles.iconBtn}
          aria-label="Toggle theme"
          onClick={toggleTheme}
        >
          {theme === "dark" ? <Sun size={16} aria-hidden /> : <Moon size={16} aria-hidden />}
        </button>
        <button type="button" className={styles.iconBtn} aria-label="Help" title="Help">
          <HelpCircle size={16} aria-hidden />
        </button>
        <div className={styles.avatarWrap}>
          <button
            type="button"
            className={styles.iconBtn}
            aria-label="Account menu"
            aria-haspopup="menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <CircleUser size={18} aria-hidden />
          </button>
          {menuOpen && (
            <div role="menu" className={styles.menu}>
              <button
                role="menuitem"
                type="button"
                className={styles.menuItem}
                onClick={signOut}
              >
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
