import styles from "./AppShell.module.css";

/**
 * Environment banner. Renders ONLY when VITE_ENV === "sandbox" — the var is
 * not defined in today's deployments, so the default is hidden (a
 * `!== "production"` check would wrongly show the banner in production).
 */
export default function EnvBanner() {
  if (import.meta.env.VITE_ENV !== "sandbox") return null;
  return (
    <div className={styles.envBanner} role="status">
      Sandbox environment
    </div>
  );
}
