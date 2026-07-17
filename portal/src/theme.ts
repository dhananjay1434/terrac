// Theme persistence: localStorage first, then OS preference. The attribute
// lives on <html> so the [data-theme="dark"] token remap applies everywhere.
export type Theme = "light" | "dark";

const THEME_KEY = "tc_theme";

export function getTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === "light" || stored === "dark") return stored;
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

export function setTheme(t: Theme): void {
  localStorage.setItem(THEME_KEY, t);
  document.documentElement.setAttribute("data-theme", t);
}

export function initTheme(): void {
  document.documentElement.setAttribute("data-theme", getTheme());
}
