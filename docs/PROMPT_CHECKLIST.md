# TerraCipher Portal Redesign — PR Checklist

> Every PR touching `portal/**` for the UI/UX redesign must satisfy this checklist. Reviewer will reject the PR if any unchecked item is unjustified.

## PR Metadata

- [ ] **Phase**: `1 / 2 / 3 / 4 / 5 / 6 / 7` (circle one)
- [ ] **Scope statement** (one sentence, what this PR does):
- [ ] **Linked spec section**: `PORTAL_UI_UX_REDESIGN.md §___`
- [ ] **Agent prompt executed**: `AI_CODER_EXECUTION_PROMPT.md — Phase ___`
- [ ] Confirmation string from agent present in PR description: `PHASE N COMPLETE — ready for Phase N+1 approval.`

---

## 1. Guardrails — Files Untouched

Confirm via `git diff --stat`:

- [ ] Zero changes in `backend/**`
- [ ] Zero changes in `lib/**`, `android/**`, `ios/**`, `pubspec.*`
- [ ] Zero changes in `portal/src/api.ts`
- [ ] Zero changes in `portal/src/auth.ts`
- [ ] Zero changes in `portal/src/compliance.ts`
- [ ] Zero changes in `portal/src/qr.ts`
- [ ] Zero renamed / removed exports from the four files above (`git log -p` on them: no diff)
- [ ] `vite.config.ts`, `tsconfig.json`, `vitest.setup.ts` unchanged (unless phase explicitly says so)

## 2. Routes & API Contracts

- [ ] All route paths in `App.tsx` unchanged: `/login`, `/batches`, `/batches/:uuid`, `/lab/scan`, `/lab/:uuid`, `/registry`, `*`
- [ ] Every route → component mapping preserved
- [ ] Every `api.ts` function call uses **identical argument shape** as before this PR
- [ ] No new API endpoints invented
- [ ] No `BatchRow` / `BatchDetail` / `Compliance` / `MediaItem` / `ChecklistItem` / `AuthError` / `ApiError` fields fabricated

Attach evidence:
```
$ grep -rn "listBatches\|getBatch\|issueCredit\|submitLabResults\|registryPost\|uploadLabCertificate\|fetchMediaUrl\|login\|logout\|downloadExport\|listKilns" portal/src
```
Paste output confirming call sites match the baseline.

## 3. Dependencies

- [ ] No package removed from `package.json`
- [ ] No major-version bumps
- [ ] Any new dep is on the approved list:
  - `lucide-react`, `clsx`, `@radix-ui/react-*`, `cmdk`, `date-fns`
- [ ] `package-lock.json` committed and consistent

## 4. Design Tokens Discipline

Run and paste result — must be empty:
```
$ grep -rEn "#[0-9a-fA-F]{3,8}\b" portal/src --include="*.tsx" --include="*.ts" --include="*.module.css" | grep -v "^portal/src/styles.css"
$ grep -rEn "[0-9]+px" portal/src --include="*.tsx" --include="*.ts" | grep -v -E "(node_modules|dist|test)"
$ grep -rEn "[0-9]+ms" portal/src --include="*.tsx" --include="*.ts" | grep -v -E "(node_modules|dist|test)"
```

- [ ] No hardcoded hex colors outside `styles.css`
- [ ] No hardcoded `px` values in new components (tokens only)
- [ ] No hardcoded `ms` durations (motion tokens only)
- [ ] Every new number/hash/timestamp render uses `.mono` and/or `.tabular` class

## 5. TypeScript & Build

- [ ] `npm run typecheck` — 0 errors (attach output)
- [ ] `npm run build` — succeeds (attach output tail)
- [ ] No `any` in new code (grep confirms):
  ```
  $ grep -rn ": any\b\|as any\b" portal/src/components portal/src/pages | grep -v test
  ```
- [ ] No `@ts-ignore` / `@ts-expect-error` added without a comment justification

## 6. Tests

- [ ] `npm run test` — all pass (attach output)
- [ ] Every new component has a `*.test.tsx` next to it
- [ ] No existing test assertion deleted (verify with `git log -p '**/*.test.tsx'`)
- [ ] New tests cover:
  - [ ] Happy path render
  - [ ] Loading state
  - [ ] Empty state
  - [ ] Error state (where applicable)
  - [ ] Keyboard interactions (Tab, Enter, Esc, arrows)
  - [ ] Auth error → redirect
  - [ ] Role-gated UI shows/hides correctly
- [ ] Coverage for new files ≥ 80% (attach `--coverage` summary; Phase 7 only enforces globally)

## 7. Accessibility

- [ ] Every interactive element has a visible focus ring
- [ ] Every icon-only button has `aria-label`
- [ ] Every mono hash/UUID render has `aria-label` explaining what it is
- [ ] Color is never the sole status indicator (dot + text OR icon + text)
- [ ] Focus is trapped in modals; returns to trigger on close
- [ ] Skip-to-content link present (Phase 1 onward)
- [ ] `prefers-reduced-motion` respected on all animations
- [ ] Phase 7 only: `jest-axe` reports 0 violations on every page (attach report)

## 8. Visual & UX QA

Attach screenshots (light + dark) for every route touched:
- [ ] `/batches`
- [ ] `/batches/:uuid`
- [ ] `/lab/scan`
- [ ] `/lab/:uuid`
- [ ] `/registry`
- [ ] `/login`

Verify manually:
- [ ] Sidebar collapse persists across reload
- [ ] Theme toggle persists across reload
- [ ] `EnvBanner` visible when non-production, hidden in production
- [ ] Breadcrumbs correct on every route
- [ ] No console errors on any route
- [ ] No console warnings introduced by this PR
- [ ] No layout shift > 0.1 CLS on initial load

## 9. Copy & Content

- [ ] No user-facing string changed unless spec explicitly directs it
- [ ] No hardcoded / faked data (kiln counts, tCO₂e totals, activity events) not backed by the API
- [ ] Timestamps rendered in UTC + local, mono font, ISO-ish format
- [ ] No emoji introduced

## 10. Security & Privacy

- [ ] No token, hash, GPS coord, or PII logged to console
- [ ] No `dangerouslySetInnerHTML` added
- [ ] No `eval`, `new Function`, or dynamic imports of user input
- [ ] Blob URLs from `fetchMediaUrl` revoked on component unmount (verify with a test)
- [ ] Clipboard writes always user-initiated
- [ ] No `.env*` file committed

## 11. Print Styles (Phase 7)

- [ ] Browser print preview of `/batches/:uuid` renders as a clean single-doc evidence pack
- [ ] Sidebar, topbar, filter bar, action buttons all hidden in print
- [ ] Hashes and timestamps remain in mono
- [ ] Colored status uses shape/icon fallback (some auditors print B&W)

## 12. Rollback Plan

- [ ] Commit history is atomic per phase task (one green commit per task)
- [ ] Reverting this PR restores the previous UI without breaking any route
- [ ] No DB migration, no config change, no infra change touched by this PR

## 13. Reviewer Sign-off

- [ ] Design reviewer approved screenshots against spec
- [ ] Engineering reviewer confirmed guardrails
- [ ] Product reviewer confirmed no copy or workflow regression

---

## Reject-on-sight signals for reviewer

Reviewer must reject the PR immediately if any of:
- `git diff --stat` shows any file in the Do-NOT-touch list
- Any `api.ts` function call signature changed
- New `any` types, `@ts-ignore`, or `console.log`s slipped in
- Hardcoded hex/px/ms in `.tsx` files
- Tests deleted or `.skip`'d
- Screenshots missing for touched routes
- Confirmation string missing from PR body

---

## Agent self-check block (paste into every PR description)

```
Phase: ___
Spec section(s): ___
Files added: ___
Files modified: ___
Files deleted: ___ (must be 0 unless replaced by a superset component)
Existing tests passing: yes/no
New tests added: ___
Guardrail violations: none
Blocked questions surfaced: none / see comments
Confirmation: PHASE N COMPLETE — ready for Phase N+1 approval.
```
