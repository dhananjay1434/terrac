/** Single source of truth for chart color tones. Charts pull a tone by
 * index from this scale instead of hardcoding a `var()` string inline, so a
 * future palette change (e.g. more/fewer stops) touches only this file.
 *
 * Brand-only: indigo is our one on-brand hue (--indigo-600 is THE brand
 * accent, used everywhere else in the UI — buttons, links, the logo). A
 * chart introducing a different hue (e.g. green/amber) would read as
 * off-brand, so every stop here stays within the indigo family. Ordered
 * darkest/most-prominent first — index 0 is meant for the segment that
 * should draw the eye first (e.g. the "hero" value in a stacked chart).
 */
export const INDIGO_CHART_SCALE = [
  "var(--indigo-600)",
  "var(--indigo-900)",
  "var(--indigo-400)",
  "var(--indigo-200)",
] as const;

/** Returns the Nth chart tone, cycling if `index` exceeds the scale length. */
export function indigoTone(index: number): string {
  return INDIGO_CHART_SCALE[index % INDIGO_CHART_SCALE.length];
}

/** Categorical tones for MULTI-SERIES charts only (e.g. 4 thermocouples on one
 * chart) — single-series charts must keep using `indigoTone`/`INDIGO_CHART_SCALE`.
 * Reuses the existing ember and verde token scales (already defined in
 * tokens.css for exactly this "brand-warm accent" purpose) rather than
 * inventing a new hue — per the no-new-brand-hue rule, indigo/ember/verde/amber
 * are all tokens that already exist. */
const CATEGORICAL_SCALE = [
  "var(--indigo-600)",
  "var(--ember-600)",
  "var(--verde-500)",
  "var(--amber-700)",
] as const;

/** Returns the Nth categorical tone, cycling if `index` exceeds the scale length. */
export function categoricalTone(index: number): string {
  return CATEGORICAL_SCALE[index % CATEGORICAL_SCALE.length];
}
