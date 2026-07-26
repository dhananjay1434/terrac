// Single source of truth for every human-readable number/date in the portal.
// Audit findings D1/B5/BD11/BD15/BD16 — one format per fact, everywhere.

const CREDIT_FMT = new Intl.NumberFormat(undefined, {
  minimumFractionDigits: 3,
  maximumFractionDigits: 3,
  useGrouping: true,
});

/** Carbon-credit figure: grouped, always 3 decimals — "1,234.560". */
export function fmtCredit(t: number): string {
  return CREDIT_FMT.format(t);
}

/** Weight in kg: grouped, ≤1 decimal — "85,000 kg". */
export function fmtKg(kg: number): string {
  const s = new Intl.NumberFormat(undefined, {
    maximumFractionDigits: 1,
    useGrouping: true,
  }).format(kg);
  return `${s} kg`;
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

/** "02 Feb 2026" (UTC), or "—" for missing. */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  return `${String(d.getUTCDate()).padStart(2, "0")} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

/** "02 Feb 2026, 10:05 UTC", or "—" for missing. */
export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${fmtDate(iso)}, ${hh}:${mm} UTC`;
}

/** "92.4%" — one decimal max. */
export function fmtPct(p: number): string {
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(p)}%`;
}
