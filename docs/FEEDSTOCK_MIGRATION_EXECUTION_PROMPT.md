# Feedstock Migration — Agent Execution Prompt

**Mission:** remove the hard-coded `Lantana_camara` feedstock from the entire product and
replace it with a **project-scoped, positive-list-validated feedstock** chosen at project
registration in the portal, resolved at runtime by the app, and never silently mis-priced by
the credit engine. Long-term, scalable, additive. **Not** a demo hack.

This prompt is written so a weak agent can execute it **one PART at a time** without holding
the whole system in its head. Follow it literally. Do not improvise beyond it. If a step's
reality does not match what's written here, **stop and report** — do not guess.

---

## 0. LOAD-BEARING RULES (read every time — these override any instinct)

1. **One PART = one commit.** Never combine PARTs. Never start the next PART until the current
   one's DoD is met and all three test suites are green.
2. **Test-first for pure logic.** Write the failing test, then the implementation, then make it
   green. Pure functions (no DB/HTTP) get unit tests with no fixtures.
3. **Additive, non-breaking migrations only.** New columns are **nullable**. Every migration has
   a real `downgrade()`. Generate the revision with `python -m alembic revision -m "slug"` —
   **never hand-write a revision id**, never hand-pick `down_revision` (alembic fills it).
4. **Grandfather everything.** A `NULL` new column = legacy row = **exactly today's behavior**.
   Prove it with a regression test.
5. **Reuse the rails; never duplicate.** This repo already has the patterns you need — mirror
   them (exact files named per PART). No new frameworks, no new HTTP clients, no god files.
6. **Never invent domain values.** Do not invent a Corg factor, a species, or a methodology
   number. The positive list is `RegistryConfig.corg_table` — that is the ONLY source of truth
   for valid species.
7. **Never fake completion.** If you cannot make a step's tests pass honestly, report the
   blocker. Do not weaken an assertion to make it green.
8. **Three-suite verification** before AND after each PART:
   ```bash
   cd backend && python -m pytest -q
   flutter test
   cd portal && npm test -- --run && npx tsc --noEmit
   ```
9. **Do not push.** Commit only. A human pushes.
10. **Commit message trailer:** end every commit body with
    `Co-Authored-By: Claude <noreply@anthropic.com>`.

---

## DECISIONS BAKED IN (a human may flip these — if so, adjust the affected PART only)

- **D1 — Storage shape:** feedstock is stored on the Project as a **JSON list**
  (`allowed_feedstocks`), even though the v1 portal UI selects exactly one. Rationale: storing a
  list now avoids a second migration when multi-feedstock projects arrive. The app treats a
  single-element list as "locked" (today's UX) and a multi-element list as a constrained picker.
- **D2 — Client count:** `client_target` is an **informational integer** in v1 (declared at
  registration, displayed). Hard-cap enforcement (rejecting farmer N+1) is **deferred** to a
  later, separate PART — do NOT build enforcement in this migration unless a human elects it.

---

## GLOBAL PREFLIGHT (run once, before PART FM-0)

```bash
cd backend && python -m alembic heads          # RECORD this. As of writing: 25dde946cadb
grep -n "class Project(Base)" backend/models.py            # ~line 246
grep -n "class ProjectCreate\|class ProjectOut" backend/portal/schemas.py   # 33 / 46
grep -n "def create_project" backend/portal/routes.py
grep -n "def _resolve_lca_config\|def get_corg" backend/credit_engine.py backend/lca_engine.py
sed -n '20,70p' backend/routers/batches.py                 # list_parcels_for_device — the endpoint to MIRROR
sed -n '1,120p' lib/services/parcel_service.dart           # ParcelService — the app rail to MIRROR
```
Confirm all three suites are green NOW (rule 8). If anything is red before you start, **stop and
report** — you must not migrate on top of a broken tree.

---

# PART FM-0 — Close the silent-default hole (backend only, no UI)

**This is the highest-value fix and it is independent of everything else. Do it first.**

**Why:** `lca_engine.get_corg(species, corg_table)` returns `Default` (0.55) for ANY species not
in the table — no error, no flag. A typo'd or unconfigured feedstock therefore silently mints a
credit at the wrong carbon value. A VVB would fail us on this. We make an unknown species a
**provisional (blocking) reason**, not a silent default.

**⚠️ VERIFIED CONSTRAINT:** `get_corg` (in `lca_engine.py`) genuinely falls back silently —
`return lookup.get(key.casefold(), table.get("Default", ...))`. Do NOT change `get_corg` itself
(other call sites + the CSI-3.2 regression guarantee depend on its current behavior). Add the
check in the **recompute** layer instead.

**Rails to reuse:** the deriver + `c10_reasons` pattern in `credit_engine.py` (see how
`derive_sampling_compliance` was added and appended to `c10_reasons`); the resolved config is
already available in recompute as `lca_config` (credit_engine.py ~line 255).

### Steps
1. **Test-first** — `backend/tests/test_feedstock_positive_list.py`. Test a pure helper
   `services/feedstock.py::derive_feedstock_compliance(feedstock_species, corg_table, *, enforced)`
   → `(ok, reason)`:
   - species present in `corg_table` (case-insensitive, ignoring the `"Default"` key) → `(True, None)`
   - species absent / empty / None → `(False, "feedstock_not_in_positive_list")`
   - `enforced=False` → always `(True, None)` (inert override, mirror the other derivers)
2. **Implement** `backend/services/feedstock.py` as pure functions only (mirror
   `services/issuance_state.py` / `services/methodology.py` shape). Also add a pure
   `positive_list(corg_table) -> list[str]` returning sorted table keys **excluding `"Default"`**
   (reused by later PARTs).
3. **Wire into recompute** — in `credit_engine.py`, inside the C10 block that builds
   `c10_reasons`, resolve the effective table as
   `(lca_config.corg_table if lca_config is not None else CORG_TABLE)` and append
   `feedstock_not_in_positive_list` when `derive_feedstock_compliance(batch.feedstock_species, table)`
   fails.
   **⚠️ VERIFIED CONSTRAINT:** `CORG_TABLE` is currently **NOT** imported in `credit_engine.py`
   — the existing block is `from lca_engine import (calculate_carbon_credit, params_from_json,
   sign_lca_audit, lca_sign_payload_bytes)`. Add `CORG_TABLE` to that exact import block.
   `lca_config` is already in scope (assigned ~line 255 as `lca_config = await
   _resolve_lca_config(session, batch.project_id)`); reuse it, do not re-resolve.
4. **Regression pin** — a batch with `feedstock_species="Lantana_camara"` (in the default table)
   is NOT flagged; a batch with `feedstock_species="Made_up_grass"` IS flagged. Add both to a
   `credit_engine` wiring test (mirror `test_sampling_plan_wiring.py`).
5. **CHECKPOINT:** `python -m pytest tests/test_feedstock_positive_list.py -v` green, then full
   `python -m pytest -q` green (this proves no existing Lantana batch flipped).

### DoD
- [x] Unknown feedstock → `feedstock_not_in_positive_list` provisional reason (never silent Default).
- [x] Pure helper unit-tested; recompute wiring tested; existing batches unaffected (regression pin).
- [x] Full backend suite green before + after.

**DONE — 2026-07-24.** `services/feedstock.py::derive_feedstock_compliance` (pure, 10 tests),
wired into `corroboration.assemble()` as a new `feedstock_ok` param — a **core** check
(applies to every methodology, not folded into `c10_reasons`/`extra_reasons`, which CSI's gate
set can exclude). 2 wiring tests via direct ORM insert. Backend-only; 730 passed / 0 failed.

**⚠️ DISCOVERY THAT AFFECTS FM-1 — read before starting FM-1.** `schemas.py`'s
`BatchPayload.feedstock_species` already has a Pydantic `field_validator` that rejects any
species outside the **static module** `CORG_TABLE` at batch-create intake (422) — it is
**project-blind** (a single-field validator can't see sibling fields like `project_id`, and has
no DB access to look up a per-project `RegistryConfig.corg_table` anyway). Today this means: a
project registered under FM-1 with a feedstock NOT in the static default table would have every
real batch **rejected at intake**, even though FM-0's recompute-level check would have approved
it. **FM-1 must address this** — loosen or remove `validate_feedstock` in `schemas.py` (the real
enforcement now lives in FM-0's recompute-level `derive_feedstock_compliance`, which correctly
resolves the project's own `corg_table`). This was not in the original FM-1 steps below — added
as FM-1 step 0.

**COMMIT:** `feat(backend): flag off-positive-list feedstock instead of silently defaulting Corg`

---

# PART FM-1 — Feedstock + client target on the Project (backend)

**Why:** feedstock is a project-enrollment fact. Persist it on the Project, validated against the
project's positive list at registration.

**Rails to reuse:** `Project` model (`backend/models.py` ~246); `ProjectCreate`/`ProjectOut`
(`backend/portal/schemas.py` 33/46); `create_project` + `_project_row` (`backend/portal/routes.py`
~214/create_project); `services/feedstock.py::positive_list` from FM-0.

**⚠️ VERIFIED CONSTRAINT — do NOT use `_resolve_lca_config` here.** That helper loads the
Project **by id from the DB** and returns `None` if the project doesn't exist yet — but in
`create_project` the project is being created in THIS request, so `_resolve_lca_config` would
return `None` and your validation would silently pass every species (fall back to the full
table). Resolve the positive list **directly from `payload.registry_config_id`** instead
(steps below). `create_project` already imports `RegistryConfig`; it does NOT import lca_engine
— you will add one import.

### Steps
0. **First — loosen the project-blind intake validator (FM-0's discovery).** In `schemas.py`,
   `BatchPayload.feedstock_species`'s `@field_validator("feedstock_species")` (`validate_feedstock`)
   currently rejects any species outside the static module `CORG_TABLE`. Change it to only reject
   **empty/whitespace-only** strings (a basic presence check) — remove the `CORG_TABLE` membership
   check entirely. The real, project-aware positive-list enforcement is FM-0's
   `derive_feedstock_compliance` in the recompute path, which correctly resolves the batch's own
   project's `corg_table` (this validator never could, since it has no DB access or sibling-field
   visibility). Update/remove the now-obsolete test(s) asserting the old 422-on-unknown-species
   behavior at the batch-create endpoint — replace with an assertion that batch-create accepts
   an arbitrary non-empty species string, and that FM-0's recompute gate is what flags it if
   it's not in the resolved positive list.
   **⚠️ VERIFIED — the full backend suite catches this if you skip it.** A grep for
   `validate_feedstock`/`"must be one of"` finds nothing (the test doesn't reference the
   validator by name), but running the FULL suite surfaces
   `tests/test_hardening.py::test_p0_12_invalid_species_rejected` (a pre-existing P0 hardening
   test, `_valid_payload(feedstock_species="Unicorn_horn")` → asserts 422) — it fails once the
   validator is loosened. This is a deliberate, correct behavior change (see above), not a
   regression: rename/rewrite it to `test_p0_12_species_validation_moved_to_recompute`, asserting
   an arbitrary species is now ACCEPTED (200/201) and only empty/whitespace is still rejected
   (422). Do not skip running the full suite before this checkpoint — a grep alone will not find
   every affected test.
   **CHECKPOINT:** the touched test file(s) green, then the FULL backend suite green, before
   continuing to step 1.
1. `models.py` `Project`: add two nullable columns:
   - `allowed_feedstocks: Mapped[str]` (String/Text, JSON-encoded list; nullable) — `NULL` = legacy.
   - `client_target: Mapped[int]` (Integer, nullable).
2. `python -m alembic revision -m "project_feedstock_and_client_target"`; fill `upgrade()`
   (`op.add_column` ×2, nullable) + a real `downgrade()` (`op.drop_column` ×2). Mirror the style of
   `b7c1d2e3f4a5` (batch_alter_table). **Re-run `alembic heads` — exactly one head (yours).**
3. `portal/schemas.py`: `ProjectCreate` gains `allowed_feedstocks: list[str] = Field(default_factory=list)`
   and `client_target: Optional[int] = Field(None, ge=0)`. `ProjectOut` gains both
   (`allowed_feedstocks: list[str]`, `client_target: Optional[int]`). Keep `extra="forbid"`.
4. `portal/routes.py::create_project` — do the validation **before** `session.add(project)`:
   - Resolve the positive list from the payload directly: if `payload.registry_config_id` is set,
     load that `RegistryConfig` row (`select(RegistryConfig).where(config_id == payload.registry_config_id)`),
     `json.loads(row.params_json or "{}").get("corg_table")`, and take its keys. If there's no
     registry_config_id, or the row/`corg_table` is absent, fall back to the module positive list —
     `from lca_engine import CORG_TABLE` and use `positive_list(CORG_TABLE)`. (`json` is already
     imported in `routes.py`.)
   - **Validate:** every entry in `allowed_feedstocks` must be in that positive list (case-
     insensitive). Reject with `422 {"error":"feedstock_not_in_positive_list","allowed":[...]}` on
     any unknown species. Store as `json.dumps(list)`.
   - Persist `client_target` verbatim.
   - `_project_row(...)` helper: JSON-decode `allowed_feedstocks` back to a list in the response.
5. **Tests** (`backend/tests/test_portal_projects.py` — create if absent, else extend): create
   with a valid feedstock succeeds and round-trips; create with an unknown feedstock → 422;
   create with **empty** `allowed_feedstocks` still succeeds (grandfather — a project may be
   registered before feedstock is decided); `client_target` round-trips.
6. **CHECKPOINT:** file green, then full backend suite green.

### DoD
- [ ] Project stores `allowed_feedstocks` (JSON list) + `client_target`; migration additive + `downgrade`.
- [ ] Registration rejects off-positive-list feedstock at the source (422), validated against the
      project's resolved `corg_table`.
- [ ] Empty list still allowed (grandfather). Round-trips in `ProjectOut`.

**COMMIT:** `feat(backend): project-scoped allowed_feedstocks + client_target (positive-list validated)`

---

# PART FM-2 — Device-facing project resolution endpoint (backend)

**Why:** the app currently has NO way to ask the server "what feedstock does my project use?"
Build the signed read channel.

**⚠️ VERIFIED CONSTRAINT:** there is no device→project mapping in the schema; the app knows its
project only via the build-time `DMRV_PROJECT_ID` dart-define and passes it as a query param
(exactly how `GET /api/v1/parcels` works). Mirror that — take `project_id` as a query param, do
NOT invent a device→project lookup (that is PART FM-6, a separate initiative).

**Rails to reuse:** `routers/batches.py::list_parcels_for_device` (signed device GET with
`?project_id=`, `verify_signature` dependency); registration in `app_factory.py`;
`services/feedstock.py::positive_list` (FM-0).

### Steps
1. New signed endpoint — put it in `routers/batches.py` next to `list_parcels_for_device`
   (same file, same rail) OR a small new `routers/project.py` (mirror `routers/day_start.py`'s
   shape and register it in `app_factory.py`). Route: `GET /api/v1/project?project_id=...`,
   `device_id = Depends(verify_signature)`. Returns:
   ```json
   {"project_id": "...", "name": "...", "allowed_feedstocks": ["..."], "client_target": 12,
    "positive_list": ["Agricultural_waste","Lantana_camara","Wood_chips"]}
   ```
   - `allowed_feedstocks` = JSON-decoded project column (empty list if NULL).
   - `positive_list` = `positive_list(resolved corg_table)` so the app could offer the full set if
     a project hasn't pinned one yet.
   - Unknown `project_id` → `404 {"detail":"project_not_found"}`.
2. **Tests** (`backend/tests/test_project_endpoint.py`, mirror `test_dispatch_endpoint.py`'s
   signed-request helper): signed happy path returns the feedstock + positive list; unsigned
   request rejected (401/403 via the shared fixture behavior); unknown project → 404.
3. **CHECKPOINT:** file green, then full backend suite green.

### DoD
- [ ] Signed `GET /api/v1/project` returns the project's `allowed_feedstocks`, `client_target`,
      and the positive list. Registered in `app_factory.py`. Unknown project → 404.

**COMMIT:** `feat(backend): device-facing GET /api/v1/project (feedstock + positive list)`

---

# PART FM-3 — Portal registration UI: feedstock dropdown + client count (React)

**Why:** whoever registers a project must pick the feedstock **from a constrained list** (never
free text — free text is how the silent-default bug gets re-introduced upstream) and declare the
client target.

**Rails to reuse:** `portal/src/pages/Projects.tsx` (the create form + `submit()` at ~L126);
`portal/src/api.ts::createProject` (~L221); the existing form-field + `DataTable` patterns already
in `Projects.tsx`; `portal/src/pages/__tests__/Projects.test.tsx`.

**⚠️ VERIFIED CONSTRAINT — the dropdown's data source.** The portal is Bearer-authed and CANNOT
call FM-2's device-signed `GET /api/v1/project`. The species positive list reaches the portal a
different way: the backend already exposes **`GET /api/v1/portal/registry-configs`**
(`list_registry_configs`, portal/routes.py ~L455) and its `RegistryConfigOut` includes
`params: dict` (which contains `corg_table`). **But `api.ts` has NO function to call it yet** —
its `registry*` helpers hit `/registry/{kind}` (kilns etc.), not `/registry-configs`. So you must
add that fetch. Do NOT hardcode a species list in React (rule 6).

### Steps
1. `portal/src/api.ts`:
   - `createProject` body type gains `allowed_feedstocks: string[]` and `client_target?: number`.
   - **Add `listRegistryConfigs()`** → `GET /api/v1/portal/registry-configs`, typed to include
     `params: { corg_table?: Record<string, number> }`.
   - Update the `Project` type to include `allowed_feedstocks: string[]` and
     `client_target: number | null`.
2. `portal/src/pages/Projects.tsx` create form:
   - **⚠️ NOTE:** the current create form only submits `project_id` + `name` — there is **no**
     registry-config selector in it. So build the species options as the **union of
     `corg_table` keys across ALL registry configs** (from `listRegistryConfigs`), minus
     `"Default"`, deduplicated + sorted. The backend (FM-1) remains the authority — it re-validates
     the chosen species against the project's actual config and returns 422 on a mismatch, so the
     union can never let a bad value persist.
   - Add a **`<select>` feedstock dropdown** (single-select v1) populated from that union. If the
     union is empty (no registry configs exist yet), **disable it with a hint** ("Create a registry
     config first") rather than showing an empty list.
   - Add a **client-count number input** — optional, `min=0`.
   - `submit()` sends `allowed_feedstocks: [selectedFeedstock]` (or `[]` if none chosen) and
     `client_target`.
   - Surface the backend 422 `feedstock_not_in_positive_list` as a clear inline error.
3. Projects table: add a **Feedstock** column (render `allowed_feedstocks.join(", ")`) and a
   **Clients** column (`client_target ?? "—"`).
4. **Tests** (`Projects.test.tsx`): the dropdown renders options; submitting includes
   `allowed_feedstocks` + `client_target`; the table shows the feedstock. Mock the API per the
   existing test's pattern.
5. **CHECKPOINT:** `cd portal && npm test -- --run && npx tsc --noEmit && npm run build` all green.

### DoD
- [ ] Registration form has a constrained feedstock dropdown (no free text) + client-count input.
- [ ] Table shows feedstock + clients. Backend validation error surfaced. Portal suite + tsc + build green.

**COMMIT:** `feat(portal): feedstock dropdown + client count on project registration`

---

# PART FM-4 — App resolves & displays the project feedstock (Flutter)

**Why:** replace the hard-coded `'Lantana_camara'` in the app with the project's real feedstock,
fetched from FM-2, cached offline-first. **Do not** turn this into a free operator choice —
display it locked (single) or as a constrained picker (multiple).

**⚠️ VERIFIED CONSTRAINTS:**
- The hard-code is `lib/providers/lantana_sourcing_notifier.dart:142`
  (`feedstockSpecies: 'Lantana_camara'`).
- The app's project id is `String.fromEnvironment('DMRV_PROJECT_ID')`
  (`lantana_sourcing_screen.dart:317`, `moisture_verification_screen.dart:73/150`).
- The batch write already uses `sourcing.feedstockSpecies`
  (`moisture_verification_screen.dart:130`) → so once the notifier resolves the real value,
  **the entire downstream chain works with no further change.** Do NOT touch the batch-write or
  sync code.
- **⚠️ VERIFIED CONSTRAINT — feedstock is NON-NULL end to end.** `Batch.feedstock_species` is
  `nullable=False` (`backend/models.py:429`) and the app's local batch write **requires** it
  (`required String feedstockSpecies`, `lib/data/local/app_database.dart:474`). Therefore a batch
  must **never** be created with an unresolved/null feedstock — doing so crashes the write. The
  capture flow's advance MUST be gated on a resolved feedstock (step 3 below). "Resolving…" is a
  blocking state, not a passthrough.
- **Offline-first is mandatory** (field devices work with no signal): mirror `ParcelService`
  (`lib/services/parcel_service.dart`) — network fetch on success caches to SharedPreferences;
  any failure returns the cache; never throws.
- Signed GET pattern: copy `DispatchService.fetchStatus`/`fetchFacilities`'s
  `CryptoSigner.signRequestV2(method:'GET', ...)` + headers block verbatim.

### Steps
1. New `lib/services/project_service.dart` — `ProjectService.fetchProjectConfig(projectId)`:
   signed `GET /api/v1/project?project_id=...`, returns a small `ProjectConfig`
   (`allowedFeedstocks: List<String>`, `positiveList: List<String>`, `clientTarget: int?`),
   caches to SharedPreferences key `dmrv.project_config.v1.$projectId`, falls back to cache on any
   error, never throws. Mirror `ParcelService` exactly (structure, cache, error handling).
2. `lantana_sourcing_notifier.dart`:
   - Remove the hard-coded `'Lantana_camara'`.
   - In `_loadState()`, resolve feedstock: read `DMRV_PROJECT_ID`; call
     `ProjectService.fetchProjectConfig`; set `feedstockSpecies` to the single allowed feedstock
     (if exactly one) or leave it unset/selectable (if multiple). If the config is unresolved AND
     no cache exists (true offline first-run), keep `feedstockSpecies` null and let the screen show
     a "resolving feedstock…" state — **never** substitute a hard-coded species.
3. `lantana_sourcing_screen.dart`:
   - `_FeedstockBlock` shows the resolved species. Single → locked placard (as today, but the
     value comes from the project). Multiple → a constrained dropdown limited to
     `allowedFeedstocks`. Keep the `Semantics(identifier: 'feedstock-species')` for tests.
   - Replace the hard-coded "Lantana camara is the only registry-approved feedstock…" string with
     a project-driven message (single: "Feedstock for this project: {species}"; multiple: "Select
     the feedstock used for this batch").
   - **Gate the advance (non-null guarantee):** the control that leaves the sourcing step toward
     capture must be **disabled until `feedstockSpecies` is non-null** (single resolved, or one
     picked from the multi list). This is mandatory — see the NON-NULL constraint above; a batch
     can never reach the write with a null feedstock. Find the existing "continue/next" gate in
     the sourcing flow and add feedstock-resolved to its enabled-condition.
4. **Tests** (`test/` — mirror `farmer_kyc_media_test.dart` / `density_calibration_screen_test.dart`
   patterns; override the network with a fake/cached config so no real HTTP):
   - single-feedstock project → placard shows that species, locked.
   - multi-feedstock project → picker shows exactly the allowed options.
   - offline with cache → shows cached species.
   - **unresolved feedstock (no config, no cache) → the advance control is DISABLED** (proves the
     non-null gate; a batch can't be captured without a feedstock).
   - the resolved species is what gets written to the batch (assert the notifier state feeds
     `sourcing.feedstockSpecies`).
5. **CHECKPOINT:** `flutter analyze` clean on touched files; `flutter test` green.

### DoD
- [ ] No hard-coded `'Lantana_camara'` in the sourcing notifier; feedstock resolved from the
      project (FM-2), cached offline-first, never silently substituted.
- [ ] Single → locked display; multiple → constrained picker. Downstream batch write untouched.
- [ ] **Advance is gated on a non-null feedstock** — a batch can never be captured/written with a
      null feedstock (DB + local write are both non-null). Proven by a test.
- [ ] App suite green; analyze clean.

**COMMIT:** `feat(app): resolve project feedstock at runtime (remove Lantana hard-code)`

---

# PART FM-5 — De-Lantana the codebase (pure cleanup, no behavior change)

**Why:** remove every remaining `Lantana` name/string so the product is genuinely feedstock-
agnostic and no future dev copies the hard-code. **Behavior must not change** — this is rename +
default-cleanup only, proven by the suites staying green.

**⚠️ VERIFIED FOOTPRINT (fix every one; re-grep at the end to prove zero remain):**
- App names/strings:
  - `lib/providers/lantana_sourcing_notifier.dart` → rename file to `sourcing_notifier.dart`;
    `LantanaSourcingNotifier` → `SourcingNotifier`; `lantanaSourcingProvider` → `sourcingProvider`.
  - `lib/ui/screens/lantana_sourcing_screen.dart` → `sourcing_screen.dart`;
    `LantanaSourcingScreen` → `SourcingScreen`.
  - Fix imports/usages in `lib/ui/screens/dashboard_screen.dart` (import + nav ~L22/L311) and
    `lib/ui/screens/moisture_verification_screen.dart` (import + provider reads).
  - `lib/ui/screens/camera_debug_view.dart:86` — remove hard-coded `'Lantana_camara'` (use a
    neutral debug placeholder or the resolved value; this is a debug view, keep it simple but not
    Lantana-named).
  - `lib/ui/screens/proof_wallet_screen.dart:153` — `'Lantana camara (Pending)'` → a neutral
    `receipt.feedstockSpecies ?? 'Feedstock (pending)'`.
- Backend:
  - `lca_engine.py` `calculate_carbon_credit(feedstock_species="Lantana_camara")` default →
    `"Default"`. **VERIFIED SAFE:** every real caller passes `feedstock_species` explicitly —
    recompute at `credit_engine.py:570` (`feedstock_species=batch.feedstock_species`) and the LCA
    tests (e.g. `test_lca_engine.py:166`) — so no runtime behavior changes. Still, re-grep
    `calculate_carbon_credit(` in `backend/tests` and confirm none omit the arg; fix any that do.
    Leave `CORG_TABLE` and the migration seed as-is — those are DATA (the positive list), not a
    hard-code.
  - Comments referencing Lantana in `schemas.py`/`lca_engine.py` are fine to leave (documentation)
    but may be generalized if trivial.
- **VERIFIED test footprint (rename/fix all four):**
  - `test/lantana_sourcing_notifier_test.dart` → rename to `sourcing_notifier_test.dart` + update
    its imports/symbols.
  - `test/biomass_input_test.dart`, `test/harvest_lock_test.dart`,
    `test/moisture_gate_notifier_test.dart` — update their imports/symbol references to the renamed
    provider/screen (they import the old names).

### Steps
1. Do the renames + import fixes. Run `flutter analyze` — resolve every reference error until clean.
2. Do the backend default change + fix affected tests.
3. **Re-grep to prove completion:**
   ```bash
   grep -rin "lantana" lib/ backend/ --include=*.dart --include=*.py | grep -v "/tests/" | grep -viE "CORG_TABLE|corg|# |///|alembic/versions"
   ```
   The only acceptable remaining hits are the `CORG_TABLE` data entry + migration seed + doc
   comments. Report the final grep output in the commit body.
4. **CHECKPOINT:** all three suites green (behavior unchanged).

### DoD
- [ ] No `Lantana`-named files/classes/providers; no hard-coded `'Lantana_camara'` outside the
      `CORG_TABLE` data + migration seed. Grep output pasted in commit body.
- [ ] Behavior identical — three suites green before + after.

**COMMIT:** `refactor: de-Lantana the app + backend (feedstock-agnostic naming, no behavior change)`

---

# PART FM-6 — (SCALING, LATER — do NOT start without explicit human election)

**Runtime project identity via enrollment.** Today `DMRV_PROJECT_ID` is a build-time dart-define →
**one APK per project**. To serve a multi-project fleet, project must be resolved at runtime:
mint enrollment tokens **per project** in the portal, record `device_id → project_id` on enroll
(new column on `DeviceKey` / `EnrollmentToken`), and have the app read its project from the server
at runtime instead of the compile-time flag.

This is a **separate initiative** with its own migration, enrollment-flow changes, and security
review (a device's project scope becomes a server-enforced authz boundary). **Scope and plan it as
its own prompt when multi-project is actually needed.** FM-0…FM-5 do NOT depend on it and must not
wait for it.

---

## FINAL — after FM-0…FM-5 land

Full three-suite regression on the merged tree:
```bash
cd backend && python -m pytest -q
flutter test
cd portal && npm test -- --run && npx tsc --noEmit && npm run build
```
Then confirm the end-to-end story by hand: register a project in the portal with a feedstock →
the device (built with that `DMRV_PROJECT_ID`) shows it in sourcing → a captured batch carries it →
the compliance record prices Corg from it, and a deliberately-wrong species is flagged
`feedstock_not_in_positive_list` (FM-0). **Do not push — a human does.**
