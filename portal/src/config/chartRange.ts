import type { CreditBucketGranularity } from "../api";

/**
 * Single source of truth pairing each chart granularity with the time window
 * it's shown over. Finer granularity ⇒ shorter, more-recent window — the
 * Stripe/Grafana convention — so bars stay contiguous and dense at every
 * granularity instead of scattering a few points across a long empty axis.
 * (A true-daily view over 6 months is mostly empty for artisanal batch
 * cadence; a 30-day daily window is honest AND legible.)
 *
 * `daysBack` is used for week/day; `monthsBack` for month (calendar months,
 * so the axis lands on clean month boundaries).
 */
export interface RangeSpec {
  label: string;
  monthsBack?: number;
  daysBack?: number;
}

export const GRANULARITY_RANGE: Record<CreditBucketGranularity, RangeSpec> = {
  month: { label: "Month", monthsBack: 6 },
  week: { label: "Week", daysBack: 91 }, // ~13 weeks
  day: { label: "Day", daysBack: 30 },
};

/** Ordered options for the granularity segmented control. */
export const GRANULARITY_OPTIONS: { value: CreditBucketGranularity; label: string }[] =
  (["month", "week", "day"] as CreditBucketGranularity[]).map((g) => ({
    value: g,
    label: GRANULARITY_RANGE[g].label,
  }));

/** Compute the [from, to] window for a granularity, ending at `now`. */
export function windowFor(
  granularity: CreditBucketGranularity,
  now: Date = new Date(),
): { from: Date; to: Date } {
  const to = new Date(now);
  const from = new Date(now);
  const spec = GRANULARITY_RANGE[granularity];
  if (spec.monthsBack != null) {
    from.setMonth(from.getMonth() - spec.monthsBack);
  } else if (spec.daysBack != null) {
    from.setDate(from.getDate() - spec.daysBack);
  }
  return { from, to };
}
