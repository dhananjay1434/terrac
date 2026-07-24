/** Typed mirror of the CSS custom properties in tokens.css. These export the
 * VAR REFERENCE, not a raw value — tokens.css stays the single source of
 * truth. Use these in JS/TS (e.g. the chart kit) instead of hardcoding hex. */

export const color = {
  surfacePage: "var(--surface-page)",
  surfaceCard: "var(--surface-card)",
  surfaceSunken: "var(--surface-sunken)",
  surfaceBrandSubtle: "var(--surface-brand-subtle)",
  borderSubtle: "var(--border-subtle)",
  borderStrong: "var(--border-strong)",
  textPrimary: "var(--text-primary)",
  textSecondary: "var(--text-secondary)",
  textTertiary: "var(--text-tertiary)",
  accent: "var(--action-primary-bg)",
  accentHover: "var(--action-primary-hover)",
  statusOkFg: "var(--status-success-fg)",
  statusOkBg: "var(--status-success-bg)",
  statusWarnFg: "var(--status-warning-fg)",
  statusWarnBg: "var(--status-warning-bg)",
  statusErrFg: "var(--status-error-fg)",
  statusErrBg: "var(--status-error-bg)",
} as const;

export const space = {
  s1: "var(--space-1)",
  s2: "var(--space-2)",
  s3: "var(--space-3)",
  s4: "var(--space-4)",
  s5: "var(--space-5)",
  s6: "var(--space-6)",
  s7: "var(--space-7)",
  s8: "var(--space-8)",
} as const;

export const radius = {
  xs: "var(--r-xs)",
  sm: "var(--r-sm)",
  md: "var(--r-md)",
  lg: "var(--r-lg)",
  xl: "var(--r-xl)",
} as const;

export const type = {
  fs12: "var(--fs-12)",
  fs13: "var(--fs-13)",
  fs14: "var(--fs-14)",
  fs16: "var(--fs-16)",
  fs18: "var(--fs-18)",
  fs20: "var(--fs-20)",
  fs24: "var(--fs-24)",
  fwRegular: "var(--fw-regular)",
  fwMedium: "var(--fw-medium)",
  fwSemibold: "var(--fw-semibold)",
  fwBold: "var(--fw-bold)",
} as const;
