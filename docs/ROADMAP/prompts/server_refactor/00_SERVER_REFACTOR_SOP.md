# SERVER.PY REFACTOR — MASTER SOP (read this first, every session)

> **Purpose.** `backend/server.py` is a 2,762-line god-object (55% of the backend). This SOP
> decomposes it into small, single-purpose modules across **10 commits (R1–R10)**, one commit per
> step, with the full test suite green after every commit. It is written so a coding agent that has
> never seen this repo can execute each step **without inventing anything**.
>
> **Golden rule of this whole effort: this is a PURE RELOCATION.** You are moving code, not changing
> it. No behavior changes. No renamed fields. No re-tuned constants. No new endpoints. No schema or
> Alembic changes. If a diff changes what a byte on the wire looks like, it is WRONG — revert it.
>
> **Author's verified baseline (2026-07-12):** `cd backend && DMRV_DISABLE_DOTENV=1 python -m pytest -q`
> → **416 passed, 2 skipped, 0 failed** in ~176s. Portal: `cd portal && npm run typecheck && npx vitest run`
> → **19 passed** + `npx vite build` OK. These numbers are the gate. "Green" = **≥416 passed, 0 failed**
> (your relocations add no tests; the count must stay 416/2 unless a step's prompt says otherwise).

---

## 0. HOW TO USE THESE FILES

- The step files are `R1_*.md` … `R10_*.md` in this same folder. **Do exactly ONE step per session/commit.**
- Each step file is self-contained: it names the exact symbols to move, the source line anchors, the
  new file to create, the imports to add, the facade re-export to add, the gate to run, and the commit
  message. **Follow it literally, top to bottom.**
- If a line anchor doesn't match (line numbers drift as steps land), **locate the symbol by its name /
  quoted body, not by line number.** The symbol names are stable; the line numbers are hints.
- Never skip the gate. Never commit red. Never edit an existing test to make it pass (see §6).

---

## 1. THE MECHANISM — strangler-fig + facade (why this is safe)

Two hard facts about this codebase make a naive "cut and paste into new files" break everything.
The facade pattern neutralizes both.

**Fact A — 30+ test files import internals directly from `server`.** Not just `app`/`get_session`, but
mutable state and private helpers:
```
from server import app, get_session, init_db, UPLOAD_DIR, recompute_batch_credit,
    verify_lca_signature, _as_utc, _safe_json_async, _require_secret, _rl_prune,
    _rl_counters, _recompute_state, _RL_MAX_COUNTERS, _HMAC_SECRET, _BIG_JSON_BYTES
```
**Fact B — `portal/` imports from `server` at module load AND lazily inside functions**, and `server.py`
imports the portal router on its LAST line (2760) to dodge a circular import. This knot is import-order
fragile.

**The fix:** after you MOVE a symbol into a new module, you IMMEDIATELY RE-EXPORT it from `server.py`:

```python
# in the new module, e.g. jsonsafe.py
def _safe_json(raw, *, context: str): ...

# back in server.py, replace the original def with an import at the same logical spot:
from jsonsafe import _safe_json, _safe_json_async, _as_utc, _BIG_JSON_BYTES  # re-export (compat)
```

Because `server.py` still exposes every moved name, **every `from server import X` keeps working with
zero edits** — in tests and in portal. Mutable globals (`_rl_counters`, `_recompute_state`) are dicts
mutated **in place**; a re-exported reference is the *same object*, so `server._rl_counters` and
`middleware._rl_counters` point at one dict — tests that poke the counter still see the live state.

This is what lets us migrate one domain per commit with the suite green the whole way, each commit
independently revertible. `server.py` shrinks from a 2,762-line implementation to a ~40-line
**composition root + compatibility facade** by R10.

---

## 2. TARGET MODULE LAYOUT (the finished shape after R10)

Flat modules + an `APIRouter` seam — the SAME convention the repo already uses (`db.py`, `storage.py`,
`observability.py`, and the `portal/` package seamed in P2.0). We are NOT introducing a foreign
`app/` mega-package.

```
backend/
  settings.py          # R2  env load, _require_secret, feature flags, all module constants (live-env readers)
  jsonsafe.py          # R1  _safe_json, _safe_json_async, _as_utc, _BIG_JSON_BYTES
  geo.py               # R1  haversine_km, _exif_to_decimal, _parse_exif_gps, _gps_mismatch_km, _evaluate_anchor, GPS_ANCHOR_MISMATCH_KM
  security.py          # R3  _b64url_decode, verify_signature, verify_media_signature, _require_admin, _SAFE
  schemas.py           # R4  ALL Pydantic request/response models (backend-level)
  credit_engine.py     # R5  recompute_batch_credit, _recompute_batch_credit_impl, _recompute_slot, _recompute_state,
                        #     _RECOMPUTE_STATE_CAP, _recompute_run_count, _device_registered_at, verify_lca_signature
  services/
    __init__.py        # R6
    registry.py        # R6  upsert_kiln/_operator_training/_supervisor_visit/_scale_calibration/_annual_verification, _find_by_payload_key
    lab.py             # R6  apply_lab_results
    compliance.py      # R6  compliance_view (+ its _COMPLIANCE_CATALOG / provenance helpers)
    evidence.py        # R6  _assert_batch_ownership, _upsert_one_to_one_evidence, _recompute_if_batch_exists, _assert_same_uuid
  middleware.py        # R8  _limit_body_size, _rate_limit, _rl_* helpers, _rl_counters, rate-limit constants
  routers/
    __init__.py        # R8
    health.py          # R8  /api/health, /metrics
    devices.py         # R8  register_device, mint_enrollment_token
    batches.py         # R8  create_batch
    evidence.py        # R8  telemetry, yield, moisture, composite, transport, metadata, application (7 routes)
    media.py           # R8  upload_media
    lab.py             # R8  ingest_lab_hcorg, ingest_lab_results
    admin.py           # R8  kiln, operator-training, supervisor-visit, scale-calibration, annual-verification (5 routes)
    compliance.py      # R8  batch_compliance
  app_factory.py       # R9  create_app() -> FastAPI: app object + CORS + middleware (exact order) + lifespan + include all routers + portal
  server.py            # R10 ~40-line facade: `from app_factory import app` + re-export the full compat surface
```

**Dependency direction (must stay one-way, no cycles):**
```
settings, jsonsafe, geo            (leaves; import only stdlib + hmac_keys/piexif)
   ↑
security, schemas                  (import leaves + db + models)
   ↑
credit_engine                      (imports models, corroboration, lca_engine, emission_factors, geo, jsonsafe, settings)
   ↑
services/*                         (import credit_engine, schemas, models, corroboration)
   ↑
middleware, routers/*              (import everything below)
   ↑
app_factory                        (imports middleware + routers + portal.routes)
   ↑
server.py (facade)                 (imports app_factory + re-exports)
```
`portal/routes.py` imports from `schemas` + `services/*` (R7) — **never from `server` again**.

---

## 3. FULL SYMBOL INVENTORY (source of truth — where every symbol goes)

Verified against `server.py` @ 2,762 lines on 2026-07-12. Column "Step" = the commit that moves it.

| Symbol (in server.py) | Kind | ~Line | → Destination module | Step |
|---|---|---|---|---|
| `GPS_ANCHOR_MISMATCH_KM` | const | 165 | geo.py | R1 |
| `haversine_km` | fn | 116 | geo.py | R1 |
| `_exif_to_decimal` | fn | 125 | geo.py | R1 |
| `_parse_exif_gps` | fn | 145 | geo.py | R1 |
| `_gps_mismatch_km` | fn | 168 | geo.py | R1 |
| `_evaluate_anchor` | fn | 178 | geo.py | R1 |
| `_safe_json` | fn | 271 | jsonsafe.py | R1 |
| `_safe_json_async` | fn | 295 | jsonsafe.py | R1 |
| `_as_utc` | fn | 307 | jsonsafe.py | R1 |
| `_BIG_JSON_BYTES` | const | 292 | jsonsafe.py | R1 |
| `_load_env` | fn | 98 | settings.py | R2 |
| `_require_secret` | fn | 200 | settings.py | R2 |
| `_MIN_SECRET_LEN`, `_MIN_SECRET_UNIQUE` | const | 196-197 | settings.py | R2 |
| `_HMAC_SECRET`, `_ADMIN_SECRET` | const | 234-235 | settings.py | R2 |
| `_attestation_enforced` | fn | 246 | settings.py | R2 |
| `_canonical_skew_seconds` | fn | 256 | settings.py | R2 |
| `_require_canonical_v2` | fn | 260 | settings.py | R2 |
| `log` (logging.getLogger) | const | 264 | settings.py | R2 |
| `_b64url_decode` | fn | 666 | security.py | R3 |
| `verify_signature` | fn | 670 | security.py | R3 |
| `verify_media_signature` | fn | 743 | security.py | R3 |
| `_require_admin` | fn | 2503 | security.py | R3 |
| `_SAFE` | const | 304 | security.py | R3 |
| `BatchPayload`, `BatchResponse`, `MediaUploadResponse` | model | 508,595,607 | schemas.py | R4 |
| `RegistrationRequest`, `RegistrationResponse` | model | 613,618 | schemas.py | R4 |
| `MintTokenRequest` | model | 853 | schemas.py | R4 |
| `LabHCorgRequest`, `LabResultsRequest` | model | 886,894 | schemas.py | R4 |
| `_BatchScopedPayload` + 7 evidence payloads | model | 2172-2304 | schemas.py | R4 |
| `KilnRequest`, `OperatorTrainingRequest`, `SupervisorVisitRequest`, `ScaleCalibrationRequest`, `AnnualVerificationRequest` | model | 2521-2608 | schemas.py | R4 |
| `_recompute_slot`, `_recompute_state`, `_RECOMPUTE_STATE_CAP` | fn/state | 1024,1020,1021 | credit_engine.py | R5 |
| `recompute_batch_credit` | fn | 1040 | credit_engine.py | R5 |
| `_recompute_batch_credit_impl` (369 LOC) | fn | 1087 | credit_engine.py | R5 |
| `_recompute_run_count` | state | 1071 | credit_engine.py | R5 |
| `_device_registered_at` | fn | 1074 | credit_engine.py | R5 |
| `verify_lca_signature` | fn | 1456 | credit_engine.py | R5 |
| `upsert_kiln` | fn | 1509 | services/registry.py | R6 |
| `_find_by_payload_key` | fn | 1536 | services/registry.py | R6 |
| `upsert_operator_training` | fn | 1551 | services/registry.py | R6 |
| `upsert_supervisor_visit` | fn | 1581 | services/registry.py | R6 |
| `upsert_scale_calibration` | fn | 1613 | services/registry.py | R6 |
| `upsert_annual_verification` | fn | 1632 | services/registry.py | R6 |
| `apply_lab_results` | fn | 1469 | services/lab.py | R6 |
| `compliance_view` (+ catalog/provenance it uses) | fn | 2682 | services/compliance.py | R6 |
| `_assert_batch_ownership` | fn | 1681 | services/evidence.py | R6 |
| `_upsert_one_to_one_evidence` | fn | 1722 | services/evidence.py | R6 |
| `_recompute_if_batch_exists` | fn | 1766 | services/evidence.py | R6 |
| `_assert_same_uuid` | fn | 2150 | services/evidence.py | R6 |
| `_limit_body_size` | mw | 365 | middleware.py | R8 |
| `_rate_limit` | mw | 462 | middleware.py | R8 |
| `_rl_prune`, `_rl_int`, `_rl_enabled`, `_rl_window_seconds`, `_rl_now`, `_rl_bucket` | fn | 406-447 | middleware.py | R8 |
| `_rl_counters`, `_RL_MAX_COUNTERS`, `_RL_DEFAULT_CAPS`, `_RL_CAP_ENV` | state/const | 402,403,393,394 | middleware.py | R8 |
| `_MAX_JSON_BODY_BYTES`, `_MAX_MEDIA_BODY_BYTES` | const | 360,361 | middleware.py | R8 |
| `health`, `metrics` | route | 625,645 | routers/health.py | R8 |
| `register_device`, `mint_enrollment_token` | route | 801,859 | routers/devices.py | R8 |
| `create_batch` (193 LOC) | route | 1794 | routers/batches.py | R8 |
| 7 evidence routes (`create_telemetry`/`_yield`/`_metadata`/`_application`/`_moisture`/`_composite_sample`/`_transport_event`) | route | 2306-2465 | routers/evidence.py | R8 |
| `upload_media` (163 LOC) | route | 1987 | routers/media.py | R8 |
| `ingest_lab_hcorg`, `ingest_lab_results` | route | 929,963 | routers/lab.py | R8 |
| 5 admin routes (`register_kiln`/`_operator_training`/`_supervisor_visit`/`_scale_calibration`/`_annual_verification`) | route | 2558-2626 | routers/admin.py | R8 |
| `batch_compliance` | route | 2728 | routers/compliance.py | R8 |
| `_parse_dt` | fn | 2510 | routers/admin.py (local helper) | R8 |
| `lifespan`, `app = FastAPI(...)`, CORS block, `_ALLOWED_ORIGIN` | assembly | 321-354 | app_factory.py | R9 |
| `UPLOAD_DIR` | const | 502 | app_factory.py (or settings.py) — see R9 | R9 |

**Anything not in this table stays where it is** (the local-module imports at server.py:50–96 get
distributed to whichever module needs them; the facade keeps a copy for re-export).

---

## 4. ENVIRONMENT & GATES (identical every step)

- Work from repo root `flutter_dmrv/`. Backend lives in `backend/`.
- **G1 — Backend (MANDATORY every step):**
  `cd backend && DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **≥416 passed, 0 failed** (~3 min; use a long timeout / background run).
  - **DO NOT export `DMRV_HMAC_SECRET` / `DMRV_ADMIN_SECRET` yourself** — `tests/conftest.py` sets them
    via `setdefault` (`test-secret` / `test-admin-secret`). Exporting your own fails every auth test
    (a false ~29-failure scare has happened before).
  - conftest also sets `DMRV_SKIP_MIGRATIONS=1`, `DMRV_RATELIMIT_ENABLED=0`, `DMRV_ALLOW_WEAK_SECRETS=1`.
- **G2 — Portal (only on R7, which touches `portal/`):**
  `cd portal && npm run typecheck && npx vitest run` → **19 passed**; `npx vite build` → OK.
- **G3 — Import sanity (fast pre-check, run before G1 every step):**
  `cd backend && DMRV_DISABLE_DOTENV=1 python -c "import server; from server import app; print('ok')"`
  → prints `ok`. If this throws (circular import / missing re-export), fix before running the suite.
- **G4 — Facade completeness audit (run on R10, useful anytime):**
  `cd backend && DMRV_DISABLE_DOTENV=1 python -c "import server; [getattr(server,n) for n in ['app','get_session','init_db','UPLOAD_DIR','recompute_batch_credit','verify_lca_signature','_as_utc','_safe_json_async','_require_secret','_rl_prune','_rl_counters','_recompute_state','_RL_MAX_COUNTERS','_HMAC_SECRET','_BIG_JSON_BYTES']]; print('facade ok')"`
- There is **no lint config** (no ruff/pyproject) enforced in CI for this; match existing style (4-space
  indent, `from __future__ import annotations` at top of each new module, docstring per module).
- **No new dependencies.** `requirements.txt` is unchanged by this entire effort.
- **No Alembic migration** anywhere in R1–R10. If you think you need one, you've misread the step — stop.

---

## 5. THE PER-STEP LOOP (do this every time — the SOP)

1. **Re-read the target symbols in `server.py` by name** (not line number). Copy them VERBATIM.
2. **Create the new module** with: module docstring, `from __future__ import annotations`, the minimal
   imports that symbol-set actually needs (copy the relevant import lines from server.py's header block),
   then the pasted symbols — byte-for-byte, comments included.
3. **In `server.py`, DELETE the original definitions** and, at the same logical location, **add a
   re-export import** from the new module (so the compat surface is preserved). See each step for the
   exact import line.
4. Run **G3 (import sanity)**. Fix any circular import before proceeding.
5. Run **G1 (full suite)**. Must be **≥416 passed, 0 failed**. (On R7 also run **G2**.)
6. **Commit** — one commit, this step only. Message format in §7. Co-author trailer required.
7. **Tick this step's box** in `PLAYBOOK_PROGRESS.md` (the P4.8 line) in the SAME commit.
8. Report a 3-line summary (what moved, LOC delta in server.py, gate result).

**If the suite goes red:** do NOT edit the test. The relocation is a pure move; a red test means either
(a) a symbol wasn't re-exported → add it to the facade import; (b) a needed import wasn't copied into the
new module → add it; (c) a circular import → the symbol is in the wrong module or needs to move later.
Revert and re-read the dependency direction in §2. The move is always the thing that's wrong, never the test.

---

## 6. HARD FENCES (violating any of these fails the step)

1. **Pure relocation only.** Do not rename, retype, reorder-args, re-tune a constant, "clean up," or
   "improve" any moved symbol in the same commit. Byte-for-byte moves.
2. **HTTP contract frozen.** Same paths, methods, status codes, JSON keys, headers, response models.
   The existing route tests are the proof; they must pass untouched.
3. **No schema / Alembic / models.py / Ed25519 / HMAC-canonical changes.** This is code layout only.
4. **Middleware order is behavioral — preserve it exactly.** Current order (outermost→innermost) is:
   `_limit_body_size` (added first) then `_rate_limit`, plus CORS and observability's request-id
   middleware. R9 reproduces the identical registration order. Do not reorder.
5. **Live-env config stays live.** The rate-limit readers (`_rl_int`/`_rl_enabled`/`_rl_window_seconds`)
   and flag readers (`_attestation_enforced`/`_require_canonical_v2`) read `os.environ` **on every call**
   so they survive `importlib.reload(server)` (several tests reload the module). Keep them as functions
   reading env at call time — never freeze them into import-time constants.
6. **Never weaken or edit a test.** (See §5.) Zero test-file edits across R1–R10 except where a step
   file *explicitly* says so (none currently do; R7 edits `portal/` source, not tests).
7. **The facade re-exports everything moved.** After each step, `from server import <anything that
   worked before>` still works. G4 is the backstop.
8. **One task = one commit = one green gate.** Never batch two R-steps into one commit.

---

## 7. COMMIT PROTOCOL

- Branch: stay on the current working branch (`feature/t5-india`) unless told otherwise. Do not create
  new branches per step.
- One commit per step. Message:
  ```
  refactor(backend): extract <what> into <module> — server.py <N>→<M> LOC (P4.8/R<k>)

  Pure relocation, no behavior change. Suite green (416 passed, 2 skipped).
  Facade re-exports preserve `from server import ...` for tests + portal.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```
- Tick the R-step checkbox in `docs/ROADMAP/PLAYBOOK_PROGRESS.md` (P4.8 sub-tracker, added by R0/first
  step) in the same commit.
- Push if the session's convention is to push (this branch tracks `origin/feature/t5-india`).

---

## 8. STEP INDEX (execute in this exact order — each depends on all prior)

| Step | File | Moves | server.py after (approx) |
|---|---|---|---|
| R1 | `R1_extract_leaf_utils.md` | jsonsafe.py + geo.py | ~2,600 |
| R2 | `R2_extract_settings.md` | settings.py (env/secrets/flags/consts) | ~2,470 |
| R3 | `R3_extract_security.md` | security.py (auth deps) | ~2,330 |
| R4 | `R4_extract_schemas.md` | schemas.py (all Pydantic models) | ~1,980 |
| R5 | `R5_extract_credit_engine.md` | credit_engine.py (the 450-LOC core) | ~1,530 |
| R6 | `R6_extract_services.md` | services/{registry,lab,compliance,evidence}.py | ~1,180 |
| R7 | `R7_repoint_portal.md` | portal/routes.py imports → schemas/services (break the cycle) | ~1,180 |
| R8 | `R8_extract_routers.md` | middleware.py + routers/*.py (21 handlers) | ~250 |
| R9 | `R9_app_factory.md` | app_factory.py (create_app + assembly) | ~60 |
| R10 | `R10_shrink_facade.md` | final facade + full audit | ~40 |

**Do not start a step until the prior step is committed and green.** If you are resuming, run G1 first to
confirm the last landed step is actually green, then open the lowest-numbered unchecked step file.
