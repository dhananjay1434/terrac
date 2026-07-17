// Single source of truth for rendering a carbon-credit figure, so the same
// number never appears at two different precisions on one screen.
export function fmtCredit(t: number): string {
  return t.toFixed(3);
}
