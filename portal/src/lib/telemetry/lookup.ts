// Pure telemetry lookups — no React, no DOM. The scalability + correctness core
// of the chart UX (blueprint audit F4/F5): O(log n) sample lookup on a
// time-sorted series, CSV rows, and elapsed-time formatting. Components render
// this; they never reimplement it.

export type Point = [number, number]; // [epoch_ms, value]

/** Value of the sample at or nearest to time `t` in a TIME-SORTED series, via
 * binary search. Returns null when the series is empty or `t` is outside its
 * [first, last] range (a hover before/after a channel's data shows nothing for
 * that channel — absence is evidence, never interpolated). */
export function sampleAt(points: Point[], t: number): number | null {
  const n = points.length;
  if (n === 0) return null;
  if (t < points[0][0] || t > points[n - 1][0]) return null;
  let lo = 0;
  let hi = n - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (points[mid][0] < t) lo = mid + 1;
    else hi = mid;
  }
  const hiIdx = lo;
  const loIdx = lo > 0 ? lo - 1 : 0;
  const dHi = Math.abs(points[hiIdx][0] - t);
  const dLo = Math.abs(points[loIdx][0] - t);
  return (dLo <= dHi ? points[loIdx] : points[hiIdx])[1];
}

/** Flatten channel series to CSV rows: a header then one row per point, sorted
 * by time then channel. `iso_ts` is ISO-8601 UTC. */
export function toCsvRows(channels: Record<string, Point[]>): string[][] {
  const rows: string[][] = [["iso_ts", "channel", "value"]];
  const flat: { t: number; ch: string; v: number }[] = [];
  for (const [ch, pts] of Object.entries(channels)) {
    for (const [t, v] of pts) flat.push({ t, ch, v });
  }
  flat.sort((a, b) => a.t - b.t || a.ch.localeCompare(b.ch));
  for (const r of flat) rows.push([new Date(r.t).toISOString(), r.ch, String(r.v)]);
  return rows;
}

/** "t+3:20" — mm:ss elapsed since burn start. Negative/NaN clamps to "t+0:00". */
export function elapsed(tStart: number, t: number): string {
  const s = Number.isFinite(t - tStart) ? Math.max(0, Math.round((t - tStart) / 1000)) : 0;
  const mm = Math.floor(s / 60);
  const ss = s % 60;
  return `t+${mm}:${ss.toString().padStart(2, "0")}`;
}
