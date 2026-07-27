# dMRV Evolution — Execution Result

**Outcome: partial — foundations landed, not the full program.** This run
completed and gated the foundation phase (M0) plus one independent M1 task
(M1.2), all with passing tests and committed. The remaining 26 tasks (M1.1,
M1.3–M6.3) are a genuine multi-week cross-stack program (per the project's own
estimate: ~2–3 weeks software-only, months including field hardware) and were
**not** executed in this session. Nothing here is fabricated — every ticked box
below has a real commit and a green test.

Why the run stopped short of "all tasks": each of the plan's six phase gates is
a full `python -m pytest` run that takes **~9 minutes** here (767 tests), and the
work includes serialized migrations, a compliance-critical credit-engine bridge,
SSE, two hand-built charts, timeline/journeys/ledgers, and a 100k-scale perf
pass. That is not completable to the plan's own quality bar (verbatim code +
per-task tests + green gates) in a single pass. The responsible result is
real, verified progress + a de-risked backlog, not a volume of ungated code.

## Manifest

| Task | Status | Note |
|---|---|---|
| M0.1 read-and-map | ✅ done | NOTES in `EXECUTION_LOG.md` (test/migration/credit-anchor patterns) |
| M0.2 feature flags | ✅ done | `feature_flags.py`, 4 tests. **Adapted**: real `AppConfig` is single-row `flags_json`, not key/value (the one permitted M0.2 deviation) |
| M0.3 replay harness | ✅ done | `tools/replay_seed.py`, slow smoke test green. Seeds scratch SQLite via `--remote` (prod-safe) |
| M1.1 schema: networks/site/kiln/batch | ✅ done | `hierarchy_v2` migration + models; 8 tests + alembic up/down/up (`46733d6`) |
| M1.2 batch-code generator | ✅ done | `batch_codes.py` verbatim + `slot_for`, 7 tests (`b824994`) |
| M1.3 backfill script | ⛔ BLOCKED | under-specified: no org_num/network_code/site_num/kiln_num mapping in schema or data; can't call `make_batch_code` without inventing one (§0.6/A3 forbids). Needs a spec |
| M1.4 hierarchy in portal list | ✅ done | `_batch_row` +3 keys; apiV2types + Batches short-code cell (`d2e13d6`) |
| M1.5 cascading filters | ✅ done | flagged `/hierarchy` + FilterBar cascading selects (`aa6fae5`); fetch wiring deferred to api2.ts (M2.6) |
| M2.1–M2.8 telemetry plane | ⬜ pending | chunks/points, ingest, read+rollup, SSE tickets, credit bridge, api2.ts, ThermalMapChart, LoadTelemetryChart |
| M3.1–M3.3 stage timeline | ⬜ pending | |
| M4.1–M4.4 distribution intelligence | ⬜ pending | |
| M5.1–M5.2 ledgers | ⬜ pending | |
| M6.1–M6.3 contract & harden | ⬜ pending | |

**Score: 8 / 30 tasks done & gated; 1 blocked (M1.3).** M0 complete; M1 complete
except M1.3 (blocked — under-specified). M1 phase gate GREEN.

### M1 phase gate (this run)
- Backend full suite: **803 passed, 2 skipped** (~950s) — up from 767 baseline
  (+36 additive tests across M0/M1), zero regressions.
- Portal `npm run verify`: tsc clean + full vitest + production build, all green.
- New Alembic head: **a7f3c1b9d2e4** (hierarchy_v2); upgrade/downgrade/upgrade
  verified on scratch SQLite. All five feature flags remain default-OFF.

## Tests (before → after)
- Backend baseline before: **767 passed, 2 skipped** (`~525s`, full run).
- Added this run: `test_feature_flags` (4 ✅), `test_batch_codes` (7 ✅),
  `test_replay_smoke` (1 ✅, slow).
- M0 phase gate (`-m "not slow"`): **771 passed, 2 skipped, 1 deselected**
  (`787s`) — that gate launched just before `test_batch_codes` was written, so
  771 = 767 + 4 (feature flags); the 7 batch-code tests were verified in a
  separate green run; the 1 slow replay test is the deselected one. Net: **778
  passing + 1 slow**, zero regressions (all changes strictly additive).
- Portal: untouched this run (still green from the prior remediation work).

## Migrations
- **None landed** (M1.1/M2.1/M3.1/M4.1 pending). Migration *pattern* mapped in
  `EXECUTION_LOG.md` (batch_alter_table, linear revision chain, up/down + scratch
  SQLite self-test). Coordinator will serialize these.

## Feature flags (all default OFF)
`telemetry_v2`, `hierarchy_v2`, `timeline_v2`, `journeys_v2`, `ledgers_v2` — all
OFF (no `AppConfig` row → `flag_enabled` returns False). Stored as keys in the
single-row `AppConfig.flags_json` (`ff.<flag>` / `ff.<flag>.<org_id>`).

## Commits
- `91d4eb7` M0 foundations (7 files, additive + conftest marker)
- `b824994` M1.2 batch codes (2 files)

## Worker stats
- Workers spawned: **0.** M0 + M1.2 are foundational, solo tasks with no
  parallel-safe siblings until the M1.1 schema lands (not reached). Parallel
  fan-out (backend module lanes | portal component lanes) begins at M1.

## De-risking delivered (accelerates the remaining 26 tasks)
- `EXECUTION_LOG.md` M0.1 NOTES: exact test-session wiring, Ed25519 signing
  canonical, migration pattern, and the **credit-engine telemetry anchor at
  `credit_engine.py:511-519`** (the M2.5 bridge injection point).
- Confirmed audit premises against code: `chartPalette.indigoTone` exists (A6);
  `Batch` has no `org_id` — it lives on `Facility`/`Project` (A4 resolution path
  correct); no existing `EventSource` (A1 greenfield).
- Found + resolved a production-safety footgun: any seed/replay must use
  `--remote <sqlite>` (bypasses `.env`, which holds a live Render Postgres URL).

## What a human must do next
1. **Hardware program (the long pole):** order 4 thermocouples (3 interior + 1
   base) + a heat-isolated load cell per pilot kiln; solving the load-cell-under-
   a-470 °C-kiln mounting is the biggest unknown. Software is ready to receive
   the data once M2 lands.
2. **Ratify the multi-thermocouple compliance rule** (blocks M2.5): which
   channels the ≥350 °C / min-temp gate evaluates. Recommended: interior
   channels (T1–T3) drive compliance, base (T4) is context only — carbon-
   methodology sign-off required.
3. **`[VERIFY]` emissions factors** (M4.2) with founders before production.
4. **Per-org flag rollout plan** — all five flags ship OFF; enable per pilot org.
5. **Continue execution** from M1.1 (schema migration + models) using the
   coordinator/worker loop; `EXECUTION_LOG.md` carries the context every worker
   needs.
