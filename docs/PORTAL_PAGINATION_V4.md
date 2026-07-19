# PORTAL V4 — Scalable Cursor Pagination for the Batches Table

## ROLE & GOAL

You are a senior product engineer adding **scalable, server-driven cursor
pagination** to the Batches table in the TerraCipher Verifier Portal
(`portal/` — React 18 + Vite + TS, CSS Modules + one global `styles.css`,
vitest + testing-library + jest-axe).

Two problems, one root design change:

1. **Bug:** the last table row is visually clipped (`table { overflow:
   hidden }` slicing content against the table's `border-radius`).
2. **Scale:** the table uses infinite "Load more" — rows accumulate in memory
   forever, and there is no page-position affordance. This does not scale and
   produces the clipped-tail feel.

**Chosen model (decided, do not revisit): forward/back CURSOR pagination.**
Fixed page size. "Next" uses the API's `next_cursor`. "Previous" pops a
client-held cursor stack. Only the current page is in memory (O(page size)).
No "jump to page N" — the API cursor is forward-only and **the API is not
changing.**

## THE ONE RULE ABOVE ALL — LOGIC FREEZE (API/data untouched)

- DO NOT edit `src/api.ts`, `src/auth.ts`, `src/compliance.ts`, `src/qr.ts`,
  `src/lab.ts`.
- DO NOT change `listBatches`' signature, params it accepts, the request URL,
  or the response shape. You may only change **which params the Batches page
  passes** and **when it calls it** — both already legal uses of the existing
  function.
- DO NOT invent data. Rows render from the same `BatchRow` fields as today.
- The cursor contract is fixed and already correct: `listBatches({ limit,
  status?, provisional?, before? })` → `{ batches: BatchRow[], next_cursor:
  string | null }`. `next_cursor === null` means "no more pages after this
  one." Read `src/api.ts:108-114` to confirm before you start.

Litmus test before each commit: *does the network still hit the exact same
endpoint with only `limit`/`status`/`provisional`/`before` params, and render
the same fields?* If not, revert.

## GLOBAL RULES

1. Read the target file/section verbatim before every edit; match
   `old_string` exactly.
2. Gate after every phase (run inside `portal/`): `npm test -- --run` →
   `npm run typecheck` → `npm run build`. All three green before commit.
3. One commit per phase, message given per phase. **Do NOT push** (the user
   pushes).
4. Tokens only for any color/spacing; no new token names; no `!important`; no
   new dependencies.
5. The a11y suite runs on Batches — keep it green (labelled controls, no
   contrast regressions).
6. Test edits are allowed ONLY where this document explicitly lists them.
   Any other failing test means you changed behavior you shouldn't have — fix
   the code, not the test.

---

## PHASE 1 — Fix the row-clipping bug (isolated, tiny, no behavior change)

File: `portal/src/styles.css` (the `table` rule ~line 307).

The `table` element has both `border-radius: var(--r-lg)` and `overflow:
hidden`; the last row's cell backgrounds/borders get clipped by the radius,
reading as a "half-cut" row. Fix WITHOUT removing the rounded corners:

- Remove `overflow: hidden;` from the `table` rule.
- Round the corners on the actual corner cells instead, so nothing is clipped.
  Add these rules right after the `th, td` block:

```css
/* Rounded table corners without clipping the last row (overflow:hidden on
   the table sliced cell content against the radius). Round the four corner
   cells directly instead. */
thead tr:first-child th:first-child { border-top-left-radius: var(--r-lg); }
thead tr:first-child th:last-child { border-top-right-radius: var(--r-lg); }
tbody tr:last-child td:first-child { border-bottom-left-radius: var(--r-lg); }
tbody tr:last-child td:last-child { border-bottom-right-radius: var(--r-lg); }
tbody tr:last-child td { border-bottom: 0; }
```

Verify: the Batches table (8 rows today) shows every row fully, last row not
sliced, corners still rounded. No test asserts this (visual). Full suite must
stay green unchanged.

**Commit:** `fix(portal): stop last table row being clipped by border-radius overflow`

---

## PHASE 2 — Replace infinite "Load more" with cursor Prev/Next

This is the real change. It rewrites the Batches page's paging state and its
footer control. **Read `portal/src/pages/Batches.tsx` in full first.**

### 2a. Paging state model

Today: `rows` accumulates (`[...prev, ...r.batches]`), one `cursor` for the
next fetch, `load(reset)` appends. Replace with a **page window + cursor
stack**:

- `rows: BatchRow[]` — the CURRENT page only (never accumulated).
- `nextCursor: string | null` — from the last response; drives "Next".
- `prevStack: string[]` — cursors for pages already visited; drives
  "Previous". Empty stack ⇒ on page 1.
- `pageIndex: number` — 1-based, for the "Page N" label. Starts at 1.
- Keep `status`, `provisional`, `search`, `err`, `loading`, `summary` as-is.

Define a fixed page size constant near the top of the component module:
`const PAGE_SIZE = 25;` (was an ad-hoc `limit: "50"` — 25 is a sane visible
page; do not exceed what fits without excessive scroll).

### 2b. The fetch function

Replace `load(reset)` with an explicit `fetchPage(before: string | null)`
that always REPLACES rows (never appends):

```ts
const fetchPage = useCallback(
  async (before: string | null) => {
    setLoading(true);
    setErr(null);
    try {
      const params: Record<string, string> = { limit: String(PAGE_SIZE) };
      if (status) params.status = status;
      if (provisional) params.provisional = provisional;
      if (before) params.before = before;
      const r = await listBatches(params);
      setRows(r.batches);
      setNextCursor(r.next_cursor);
    } catch (e) {
      if (e instanceof AuthError) nav("/login");
      else setErr("Failed to load batches.");
    } finally {
      setLoading(false);
    }
  },
  [status, provisional, nav],
);
```

Note `before` is now a PARAMETER, not read from state — this removes `cursor`
from the dep array (a correctness win: the old `load` had `cursor` in deps,
risking stale-closure refetches).

### 2c. Navigation handlers

```ts
function goNext() {
  if (!nextCursor) return;
  // The cursor that produced the CURRENT page is prevStack's top; push the
  // current page's "before" so Previous can return here. Page 1's before is
  // null, represented by an empty stack.
  setPrevStack((s) => [...s, currentBefore]);
  setCurrentBefore(nextCursor);
  setPageIndex((n) => n + 1);
  fetchPage(nextCursor);
}
function goPrev() {
  setPrevStack((s) => {
    const copy = [...s];
    const target = copy.pop() ?? null;
    setCurrentBefore(target);
    setPageIndex((n) => Math.max(1, n - 1));
    fetchPage(target);
    return copy;
  });
}
```

Add state `const [currentBefore, setCurrentBefore] = useState<string | null>(
null);` — the `before` value that produced the visible page (null on page 1).

### 2d. Filter/tab changes RESET pagination

When `status` or `provisional` changes, or a saved view/tab is switched, the
page must return to page 1 with a fresh stack. In the existing effect that
reloads on filter change, replace `load(true)` with a full reset:

```ts
useEffect(() => {
  setPrevStack([]);
  setCurrentBefore(null);
  setPageIndex(1);
  fetchPage(null);
  setSearchParams(view && view !== "all" ? { view } : {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [status, provisional]);
```

### 2e. Search interaction (IMPORTANT — contract change)

Today search filters the accumulated in-memory rows client-side. Under
server pagination, `rows` is only the current page, so client-side search
would only search 25 rows — misleading. Decision: **client-side search now
explicitly filters the CURRENT PAGE only, and the empty-state copy must say
so.** Keep the `displayed` filter (search + blocking view) but update the
empty-state copy in the `DataTable`'s `empty` prop:

- When `q` is set and the page has rows but none match:
  title `"No matches on this page"`,
  description `"Search filters the current page only. Clear the search to page
  through all results."`
- Global empty (no rows at all) stays `"No batches found"` /
  `"Adjust the filters above, or wait for field devices to sync."`

(Do NOT try to make search server-side — `listBatches` has no search param and
the API is frozen. Page-local search with honest copy is the correct scoped
behavior.)

### 2f. The footer control (replaces "Load more")

Replace the existing footer block (the `Showing … / Load more` flex div) with
Prev / page-indicator / Next:

```tsx
<nav
  className="pager"
  aria-label="Batches pagination"
>
  <button
    className="neutral"
    type="button"
    onClick={goPrev}
    disabled={loading || prevStack.length === 0}
  >
    ‹ Previous
  </button>
  <span className="micro pager-status" aria-live="polite">
    Page {pageIndex}
    {rows.length > 0 && ` · ${rows.length} row${rows.length === 1 ? "" : "s"}`}
  </span>
  <button
    className="neutral"
    type="button"
    onClick={goNext}
    disabled={loading || !nextCursor}
  >
    Next ›
  </button>
</nav>
```

`disabled` on Previous when `prevStack.length === 0` (page 1) and on Next when
`nextCursor === null` (last page) — the two buttons cannot both be dead unless
there is exactly one page, which is correct.

### 2g. Styles

Add to `styles.css` (near the table rules):

```css
.pager {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.pager-status {
  color: var(--text-secondary);
}
```

Reuse the existing `.neutral` button style — no new button variants.

### 2h. Summary "Credit … loaded rows" hint

The summary StatTile currently sums `rows` and labels it "loaded rows". Since
`rows` is now one page, change the hint text from `"loaded rows"` to
`"this page"` so the label stays truthful. (StatTile value logic unchanged —
still `rows.reduce(...)`.) Find the `<StatTile label="Credit" … hint="loaded
rows" />` and change only the hint string.

---

## PHASE 2 TESTS — exact, enumerated edits to `Batches.test.tsx`

These test edits are REQUIRED and are the ONLY permitted test changes.

1. **`limit` value:** every `expect.objectContaining({ … limit: "50" })`
   becomes `limit: "25"` (the tests at ~line 101 assert `limit: "50"`; update
   to match `PAGE_SIZE`). If a test only asserts `status`/`provisional`
   without `limit`, leave it.

2. **The infinite-scroll empty-state test** (~line 174,
   `"empty-while-filtered copy differs from empty-global, and warns when more
   pages exist"`): its copy assertions reference the old "Load more rows"
   wording. Rewrite the assertions to the new page-local copy:
   - `findByText("No matches on this page")` (was "No matches in the loaded
     rows")
   - `getByText(/Clear the search to page through all results/)` (was /Load
     more rows, or refine your search/)
   - Keep `queryByText("No batches found")` not-in-document.
   Rename the test to `"page-local search empty copy differs from global
   empty"`.

3. **ADD one new test** proving Next/Prev drive the cursor correctly:

```ts
it("pages forward with next_cursor and back via the cursor stack", async () => {
  mockList.mockResolvedValueOnce({ batches: FIXTURE, next_cursor: "cur-2" });
  renderPage();
  await screen.findByText("dev-1");

  // Next → fetch with before=cur-2
  mockList.mockResolvedValueOnce({
    batches: [{ ...FIXTURE[0], batch_uuid: "cccc1111-2222-3333-4444-555566667777", device_id: "dev-3" }],
    next_cursor: null,
  });
  fireEvent.click(screen.getByRole("button", { name: /Next/ }));
  await screen.findByText("dev-3");
  expect(mockList).toHaveBeenLastCalledWith(
    expect.objectContaining({ before: "cur-2", limit: "25" }),
  );
  expect(screen.getByText(/Page 2/)).toBeInTheDocument();

  // On the last page, Next is disabled
  expect(screen.getByRole("button", { name: /Next/ })).toBeDisabled();

  // Previous → back to page 1 (before param absent)
  mockList.mockResolvedValueOnce({ batches: FIXTURE, next_cursor: "cur-2" });
  fireEvent.click(screen.getByRole("button", { name: /Previous/ }));
  await screen.findByText("dev-1");
  expect(mockList).toHaveBeenLastCalledWith(
    expect.not.objectContaining({ before: expect.anything() }),
  );
  expect(screen.getByText(/Page 1/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Previous/ })).toBeDisabled();
});
```

4. **Existing tests that must still pass UNCHANGED** (do not edit): skeleton
   on load, global empty state, StatusDot variants, row-click nav, filter →
   new call, copy button, blocking-issues view, AuthError → /login, tab/select
   non-contradiction, summary stat-band, summary-reject-no-crash. If any of
   these break, your implementation diverged — fix the code.

**Commit:** `feat(portal): cursor prev/next pagination for batches — scalable, page-window memory`

---

## PHASE 3 — Gate, a11y, and scope check

1. Full gate green: `npm test -- --run`, `npm run typecheck`, `npm run build`.
2. Confirm the a11y suite still passes (the pager `<nav aria-label>` and
   button names are labelled; `aria-live="polite"` on the status announces
   page changes to screen readers).
3. Scope diff check — only these files changed:
   `portal/src/pages/Batches.tsx`,
   `portal/src/pages/__tests__/Batches.test.tsx`,
   `portal/src/styles.css`.
4. Manual reasoning pass (write it in the commit body or report): confirm
   memory is O(page) — `rows` is replaced, never appended — and that filter/
   tab changes reset to page 1. No push.

## OUT OF SCOPE — DO NOT ATTEMPT

- No "jump to page N" / numbered page buttons — the API cursor is forward-only
  and the API is frozen. Prev/Next only.
- No server-side search — `listBatches` has no search param; page-local search
  with honest empty copy (2e) is the scoped, correct behavior.
- No total-count / "Page N of M" — the API does not return a total; claiming a
  total would be fabricated data. "Page N" (current only) is honest.
- No changes to filters, tabs, saved views, summary band logic, DataTable
  component, or any API call shape.
- No new dependencies, no layout-width change, no token renames.

## WHY THIS IS THE SCALABLE ANSWER (rationale, for reviewers)

- Memory is O(PAGE_SIZE), not O(all rows ever loaded) — the old "Load more"
  grew unbounded.
- Each page is exactly one existing `listBatches` call; the backend already
  cursor-paginates, so this scales to any row count with no API change.
- Prev/Next + cursor stack is the maximum navigation the forward-only cursor
  supports without fabricating a total or an offset the API doesn't provide —
  honest within the contract.
- The clipping bug (Phase 1) is fixed structurally (corner-cell radius), so it
  cannot recur regardless of row count or viewport height.
