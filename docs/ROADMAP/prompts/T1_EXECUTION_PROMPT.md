# T1 EXECUTION PROMPT — Rainbow Methodology Completion (batch→project linkage + the three dormant gates)

> **Hand this file to the implementing engineer/agent verbatim.** It is self-contained: every edit has an exact file, line anchor, and code block; every phase has a test plan and a red/green gate. Written 2026-07-07 against branch `remediation/phase-by-phase` (post-T0 assumed committed; if T0 is not done, only T0.2 — committing the in-flight P0.a diff — is a hard prerequisite, because line anchors below assume that diff is applied).

---

## 0. MISSION

Make every reason in the C10 compliance catalog **reachable**. Today 3 of 19 catalog reasons can never fire:

| Reason (catalog line) | Why dead today |
|---|---|
| `scale_calibration_expired` (server.py:2024) | deriver `derive_scale_calibration_compliance` (corroboration.py:262-273) is **never called** |
| `missing_annual_methane` (server.py:2025) | deriver `derive_annual_methane_compliance` (corroboration.py:276-287) is **never called** |
| `missing_pah` (server.py:2026) | deriver called with **hardcoded `enforced=False`** and literal `pah_measured = False` (server.py:890-895) |

Root cause for all three: `Batch` has no `project_id`/`scale_id` (admitted in the code comment at server.py:858-861). You will add that linkage end-to-end (server schema → API → Flutter client), then wire the three gates, then two small closers (lab-moisture min-3 validation, compliance-report provenance).

**You are NOT doing** (explicitly out of scope, blocked on external sign-off — do not touch): transport factor citation / `TRANSPORT_EVENTS_ENFORCED` flip (T1.5), methane rate → CH4 penalty math (T1.6), conversion-factor → yield math (T1.7), 1000-yr inertinite election (T1.8). One tiny exception allowed: removing bogus `@pytest.mark.asyncio` marks (Phase 7 below).

---

## 1. ENVIRONMENT & GATES

- Repo root: `flutter_dmrv/`. Backend: Python/FastAPI in `backend/`. Client: Flutter in `lib/`.
- **Backend gate** (run from `backend/`): `python -m pytest -q` → baseline **262 passed, 1 skipped, 0 failed**. "Green" = ≥262 passed, 0 failed, plus your new tests.
- **Client gates** (repo root): `flutter analyze` → baseline **25 issues, 0 errors** (do not add any); `flutter test` → baseline **151 passed, 2 skipped**.
- Codegen after any Drift change: `dart run build_runner build --delete-conflicting-outputs`, then confirm the new identifiers exist in `lib/data/local/app_database.g.dart`.
- Test env is self-contained (conftest.py:27-34 sets `DATABASE_URL=sqlite in-memory`, `DMRV_HMAC_SECRET=test-secret`, `DMRV_ADMIN_SECRET=test-admin-secret`, `DMRV_SKIP_MIGRATIONS=1`).
- **One phase = one commit = one green gate = one REMEDIATION_LOG.md entry** (append, follow the existing entry format). Never start a phase on a red gate.

## 2. NON-NEGOTIABLE RULES (violating any of these breaks deployed field devices)

1. **Additive only:** new *nullable* columns, new *optional* Pydantic fields. Never rename/drop/require-existing. `BatchPayload` has `extra="forbid"` (server.py:347) — old clients that omit new fields must keep working; they will, because everything you add is `Optional` with `None` default.
2. **Compliance only via the provisional model.** Never reject an upload for a methodology reason. Mechanism: derive → reason string → `c10_reasons.append(...)` → `assemble(extra_reasons=c10_reasons)` (server.py:900-915). `assemble` already de-duplicates and orders (corroboration.py:363-367).
3. **Gates must be inert for legacy data.** A batch with `project_id IS NULL` / `scale_id IS NULL` must produce **zero new reasons**. Never gate every batch spuriously.
4. **Do not modify** existing deriver signatures, the canonical signing strings, `assemble`'s existing kwargs, or any Alembic migration already on disk.
5. Alembic: current head is **`e1f2a3b4c5d6`** (annual_verifications). Your new migration's `down_revision` = `"e1f2a3b4c5d6"`. Must have a working `downgrade()`.
6. Client schema: bump `AppDatabase.schemaVersion` by **exactly 1** (22 → 23, `lib/data/local/app_database.dart:47`), one new `if (from < 23)` block, `addColumn` only.
7. Schema-shape tests must assert `greaterThanOrEqualTo(23)`, never `== 23` (a pinned `== 21` broke once already — documented gotcha).

---

## 3. VERIFIED CURRENT-STATE FACTS (anchors you will edit against)

- `Batch` model: `backend/models.py:289-335`; last client-payload fields end with `biomass_measurement_method`; `device_id` at models.py:328.
- `BatchPayload`: server.py:271-347; C1 fields at 291-295; config at 347.
- `Batch(...)` construction in `create_batch`: server.py:1167-1188 (fields end `biomass_measurement_method=..., device_id=..., status="RECEIVED"`).
- `recompute_batch_credit`: server.py:718-973. C10 block starts at the comment server.py:856-861; `c10_reasons` at 862; biomass check 864-869; kiln check 871-882 (ends `c10_reasons.append(_kiln_reason)`); PAH bypass block 884-895; `assemble(...)` call 900-915.
- Corroboration imports in server.py: block at server.py:69+ (`from corroboration import (...)`) — currently does **not** import `derive_scale_calibration_compliance` or `derive_annual_methane_compliance`; **does** import `derive_pah_compliance`.
- `ScaleCalibration` (models.py:217-242, `scale_id` :229, `valid_until` :233-235) and `AnnualVerification` (models.py:245-286, unique on `(project_id, year)` :262-264, `methane_run_count` :270, `pah_measured` :273) are **already imported** in server.py (used by the admin handlers at 1877-1902 and 1931-1986) — no models-import change needed.
- `datetime`/`timezone` already imported (server.py:20).
- Admin auth helper `_require_admin(x_admin_secret)` exists (used at server.py:2045); admin test secret literal is `test-admin-secret`.
- Admin payload shapes for tests: `ScaleCalibrationRequest` (server.py:1788+) fields include `calibration_uuid`, `scale_id`, `calibrated_at`, `valid_until` (ISO strings), `report_sha256`; `AnnualVerificationRequest` (server.py:1914-1929) fields `project_id`, `year`, `methane_rate_g_per_kg`, `methane_run_count`, `conversion_factor`, `pah_measured`, `heavy_metals_measured`, `leakage_assessment_done`, `dry_bulk_density`, `quality_oversight_sha256`, `report_sha256`; both `extra="forbid"`.
- Migration style to copy exactly: `backend/alembic/versions/e5f6a7b8c9d0_batches_biomass_input.py` (uses `op.batch_alter_table("batches")`).
- Test fixtures (backend/tests/conftest.py): `client` (httpx `SignedAsyncClient` that auto-signs as device `test-device-reg`, conftest.py:101-138), `registered_device` (enrolls that device, :141-160), `session_factory`; existing suites to extend: `test_project_registry_c8.py`, `test_annual_verification_c9.py`, `test_compliance_gate_c10.py`.
- Client: `BiomassSourcing` table `lib/data/local/tables.dart:57-100` (C1 fields at :86-92, primaryKey/uniqueKeys after); version-history doc comment around tables.dart:35. `schemaVersion => 22` at app_database.dart:47; migration blocks end with `if (from < 22)` around app_database.dart:231-234; the batch outbox writer `insertBiomassSourcingWithOutbox` builds its JSON payload at app_database.dart:352-371 (`'biomass_input_kg': biomassInputKg,` at :369).
- Compliance endpoint + catalog: server.py:1993-2073.

---

## 4. PHASE 1 — T1.1 server side: `project_id`/`scale_id` on Batch (schema + migration + API)

### 4.1 models.py

In `class Batch` (models.py:289+), immediately **after** the `biomass_measurement_method` column (i.e. with the other client-payload fields, before/near `device_id` at :328), add:

```python
    # Rainbow T1.1: batch→project/scale linkage. Resolves the project-scoped
    # gates (C8 scale calibration, C9 annual methane/PAH). Nullable — legacy
    # batches predate the linkage and those gates stay inert for them.
    project_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
    scale_id: Mapped[str] = mapped_column(String(128), nullable=True, index=True)
```

### 4.2 New migration `backend/alembic/versions/f1a2b3c4d5e6_batches_project_linkage.py`

```python
"""batches: add project_id + scale_id linkage (Rainbow T1.1)

Resolves the project-scoped C10 gates (scale calibration, annual methane, PAH)
that were dormant for lack of a batch→project/scale linkage. Both columns are
nullable/additive; legacy batches keep NULL and the gates stay inert for them.

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.add_column(sa.Column("project_id", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("scale_id", sa.String(length=128), nullable=True))
        batch_op.create_index("ix_batches_project_id", ["project_id"])
        batch_op.create_index("ix_batches_scale_id", ["scale_id"])


def downgrade() -> None:
    with op.batch_alter_table("batches") as batch_op:
        batch_op.drop_index("ix_batches_scale_id")
        batch_op.drop_index("ix_batches_project_id")
        batch_op.drop_column("scale_id")
        batch_op.drop_column("project_id")
```

### 4.3 BatchPayload (server.py:291-295 area)

After the C1 biomass fields (line 295), add:

```python
    # Rainbow T1.1: optional batch→project/scale linkage. Configured on the
    # device (dart-define) — enables the project-scoped C8/C9 gates. Old
    # clients omit these; the gates stay inert for their batches.
    project_id: Optional[str] = Field(None, min_length=1, max_length=128)
    scale_id: Optional[str] = Field(None, min_length=1, max_length=128)
```

### 4.4 create_batch persistence (server.py:1184-1185 area)

In the `Batch(...)` constructor, after `biomass_measurement_method=payload.biomass_measurement_method,` add:

```python
        project_id=payload.project_id,
        scale_id=payload.scale_id,
```

### 4.5 Tests — new file `backend/tests/test_batch_project_linkage.py`

Model the batch-POST pattern on any existing flow test (e.g. `test_biomass_input.py`). Skeleton:

```python
"""Rainbow T1.1: batch→project/scale linkage — additive & backward compatible."""
import json
import uuid as _uuid

import pytest
from sqlalchemy import select


def _batch_payload(**over):
    p = {
        "batch_uuid": str(_uuid.uuid4()),
        "feedstock_species": "Lantana_camara",   # must be a CORG_TABLE key; copy from existing tests
        "harvest_timestamp": "2026-07-01T10:00:00+05:30",
        "moisture_percent": 12.0,
    }
    p.update(over)
    return p


async def _post_batch(client, payload):
    return await client.post(
        "/api/v1/batches",
        content=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "X-Idempotency-Key": f"op-{payload['batch_uuid']}",
        },
    )


@pytest.mark.asyncio
async def test_batch_accepts_and_persists_linkage(client, registered_device, session_factory):
    payload = _batch_payload(project_id="proj-khp-01", scale_id="scale-7")
    r = await _post_batch(client, payload)
    assert r.status_code == 201
    from models import Batch
    async with session_factory() as s:
        row = (await s.execute(select(Batch).where(Batch.batch_uuid == _uuid.UUID(payload["batch_uuid"])))).scalar_one()
    assert row.project_id == "proj-khp-01"
    assert row.scale_id == "scale-7"


@pytest.mark.asyncio
async def test_legacy_payload_without_linkage_unchanged(client, registered_device, session_factory):
    payload = _batch_payload()  # no project_id/scale_id — the deployed-client shape
    r = await _post_batch(client, payload)
    assert r.status_code == 201
    from models import Batch
    async with session_factory() as s:
        row = (await s.execute(select(Batch).where(Batch.batch_uuid == _uuid.UUID(payload["batch_uuid"])))).scalar_one()
    assert row.project_id is None and row.scale_id is None
    # Crucially: no new provisional reasons appear for unlinked batches.
    reasons = json.loads(row.provisional_reasons or "[]")
    assert "scale_calibration_expired" not in reasons
    assert "missing_annual_methane" not in reasons
    assert "missing_pah" not in reasons
```

(Check `test_biomass_input.py` / `test_required_credit_inputs.py` first — if they already have a batch-payload helper, reuse their exact species/timestamp values instead of the ones above.)

**Gate → commit:** `python -m pytest -q` green (≥264 passed). Commit: `feat(dmrv): batch→project/scale linkage — server schema+API (Rainbow T1.1a)`. Journal entry in REMEDIATION_LOG.md.

---

## 5. PHASE 2 — T1.1c client side: capture + sync the linkage

### 5.1 `lib/data/local/tables.dart`

1. In the version-history doc comment (around :35), append: `///   v23: project_id + scale_id on biomass_sourcing (Rainbow T1.1).`
2. In `class BiomassSourcing`, after `biomassMeasurementMethod` (:92), add:

```dart
  // ---------- v23 project/scale linkage (Rainbow T1.1) ----------
  /// Project this device produces for (from --dart-define=DMRV_PROJECT_ID).
  /// Enables the server-side project-scoped compliance gates (C8/C9).
  TextColumn get projectId => text().nullable()();

  /// Weighing-scale identity, when known (BLE scale pairing metadata).
  TextColumn get scaleId => text().nullable()();
```

### 5.2 `lib/data/local/app_database.dart`

1. `:47` — `int get schemaVersion => 23;`
2. After the `if (from < 22)` block (:231-234), add:

```dart
      if (from < 23) {
        // Rainbow T1.1: batch→project/scale linkage.
        await m.addColumn(biomassSourcing, biomassSourcing.projectId);
        await m.addColumn(biomassSourcing, biomassSourcing.scaleId);
      }
```

3. In `insertBiomassSourcingWithOutbox`: add optional params `String? projectId, String? scaleId` to the signature; add `projectId: Value(projectId), scaleId: Value(scaleId),` to the `BiomassSourcingCompanion.insert(...)` (:332-350); add to the JSON payload map (:352-371, after `'biomass_measurement_method'`):

```dart
      'project_id': projectId,
      'scale_id': scaleId,
```

**Payload-null note:** check how the sync layer treats null JSON values before shipping: server-side `extra="forbid"` is satisfied either way (`project_id: null` is valid for an `Optional` field), so sending explicit nulls is fine — but mirror whatever the existing fields do (they send nulls, e.g. `'photo_path': photoPath`), so keep it consistent: include the keys unconditionally.

4. Run codegen: `dart run build_runner build --delete-conflicting-outputs`; confirm `projectId` appears in `app_database.g.dart`.

### 5.3 Wire the value at the call site

Find the caller: `grep -rn "insertBiomassSourcingWithOutbox" lib/ --include="*.dart"` (expect the batch-session notifier or the sourcing screen). At the call site pass:

```dart
      projectId: const String.fromEnvironment('DMRV_PROJECT_ID').isEmpty
          ? null
          : const String.fromEnvironment('DMRV_PROJECT_ID'),
      scaleId: null, // populated when BLE scale pairing exposes an identity (future)
```

(Note: `String.fromEnvironment` default is `''` — normalize empty→null so unconfigured builds stay legacy-shaped. Put the normalization in a small helper in `lib/config/` if one exists; otherwise inline is fine.)

### 5.4 Client tests

New `test/migration_v23_project_linkage_test.dart`, modeled on the existing `migration_v21_*`/`migration_v22_*` tests (copy their harness): assert schema version `greaterThanOrEqualTo(23)` (**never** `== 23`), and that a v22→v23 upgrade adds the two nullable columns; extend the outbox writer test (find the test covering `insertBiomassSourcingWithOutbox` payload keys — `grep -rn "biomass_input_kg" test/`) to assert the payload now carries `project_id`/`scale_id` keys and that passing null keeps them null.

**Gates → commit:** `flutter analyze` (still 25/0), `flutter test` green (≥153). Also rerun backend suite (client contract untouched, but cheap). Commit: `feat(dmrv): client capture+sync of project/scale linkage, schema v23 (Rainbow T1.1c)`. Journal.

---

## 6. PHASE 3 — T1.2 wire the scale-calibration gate

### 6.1 server.py corroboration imports (block at :69+)

Add `derive_scale_calibration_compliance` (and while here, `derive_annual_methane_compliance` for Phase 4) to the `from corroboration import (...)` list — keep alphabetical order of the existing list.

### 6.2 recompute_batch_credit — insert AFTER the kiln block (after :882's `c10_reasons.append(_kiln_reason)`), BEFORE the PAH comment block (:884)

```python
    # C8 (T1.2): the batch's weighing scale must have an in-date calibration.
    # Inert when the batch has no scale linkage (legacy batches / no scale_id).
    if batch.scale_id:
        _now = datetime.now(timezone.utc)
        _cal_row = (
            await session.execute(
                select(ScaleCalibration.id).where(
                    ScaleCalibration.scale_id == batch.scale_id,
                    ScaleCalibration.valid_until.is_not(None),
                    ScaleCalibration.valid_until >= _now,
                )
            )
        ).first()
        _sc_ok, _sc_reason = derive_scale_calibration_compliance(_cal_row is not None)
        if _sc_reason:
            c10_reasons.append(_sc_reason)
```

**SQLite/tz caveat:** `valid_until` is `DateTime(timezone=True)` but the test engine is SQLite (naive storage). If the comparison misbehaves in tests, compare in Python instead (fetch `valid_until` and check `row.valid_until.replace(tzinfo=timezone.utc) >= _now`) — mirror however `_parse_dt` (used at server.py:1885-1887) normalizes. Prefer whichever variant passes on BOTH the SQLite test path and reads correctly on Postgres; document the choice in the code comment.

### 6.3 Tests — extend `backend/tests/test_project_registry_c8.py`

There is an existing test asserting registry-landing changed nothing batch-side — **replace/retire the dormancy assertion for `scale_calibration_expired`** and add (reusing that file's existing batch/admin helpers):

```python
# helper: admin posts a calibration
async def _post_calibration(client, scale_id, valid_until_iso, uuid_):
    return await client.post(
        "/api/v1/admin/scale-calibration",
        json={
            "calibration_uuid": uuid_,
            "scale_id": scale_id,
            "calibrated_at": "2026-01-01T00:00:00+00:00",
            "valid_until": valid_until_iso,
        },
        headers={"X-Admin-Secret": "test-admin-secret"},
    )
```

Cases (each = create batch with `scale_id="scale-7"` via the Phase-1 payload helper, then read `provisional_reasons`):
1. **No calibration at all** → `"scale_calibration_expired" in reasons`, `batch.provisional is True`.
2. **Expired only** (`valid_until="2020-01-01T00:00:00+00:00"`) → reason present.
3. **In-date** (`valid_until="2030-01-01T00:00:00+00:00"`) → reason **absent**. (Order matters: post the calibration **before** creating the batch — recompute runs at batch creation; or re-trigger recompute by posting any evidence, e.g. `/telemetry`, after the calibration, and assert the reason cleared — this second variant is the stronger test; do both if cheap.)
4. **Legacy batch (no scale_id)** with zero calibrations in DB → reason absent.

**Gate → commit:** backend green. Commit: `feat(dmrv): enforce C8 scale-calibration expiry via batch scale linkage (Rainbow T1.2)`. Journal.

---

## 7. PHASE 4 — T1.3 wire the annual-methane gate

### 7.1 recompute — insert AFTER the Phase-3 block, BEFORE the PAH block

```python
    # C9 (T1.3): the batch's project must have a methane verification (>= 3
    # representative runs) for the batch's production year. Inert when the
    # batch has no project linkage. The verification row is reused by the PAH
    # gate below. Year policy: harvest-timestamp year (production vintage) —
    # flagged to the methodology owner in the T1.3 PR.
    annual_verif = None
    if batch.project_id:
        _verif_year = batch.harvest_timestamp.year
        annual_verif = (
            await session.execute(
                select(AnnualVerification).where(
                    AnnualVerification.project_id == batch.project_id,
                    AnnualVerification.year == _verif_year,
                )
            )
        ).scalar_one_or_none()
        _am_ok, _am_reason = derive_annual_methane_compliance(
            annual_verif.methane_run_count if annual_verif else None
        )
        if _am_reason:
            c10_reasons.append(_am_reason)
```

### 7.2 Tests — extend `backend/tests/test_annual_verification_c9.py`

That file currently **asserts the dormancy** (comment at :121, `assert "missing_annual_methane" not in reasons` at :144) — replace those assertions with the live behavior. Add cases (admin posts use `POST /api/v1/admin/annual-verification` with `X-Admin-Secret: test-admin-secret`; remember upsert key is `(project_id, year)` and the year checked is the **harvest year** of the batch payload — use `harvest_timestamp="2026-07-01..."` → `year=2026`):
1. Project-linked batch (`project_id="proj-khp-01"`), **no verification row** → `missing_annual_methane` present, provisional.
2. Verification with `methane_run_count=2` → reason present (below `MIN_METHANE_RUNS=3`).
3. Verification with `methane_run_count=3` → reason absent.
4. Verification exists for the **wrong year** (2025) → reason present.
5. Legacy batch (no `project_id`) → reason absent.

**Gate → commit:** `feat(dmrv): enforce C9 annual-methane (>=3 runs) via batch project linkage (Rainbow T1.3)`. Journal (include the year-policy decision).

---

## 8. PHASE 5 — T1.4 un-bypass the PAH gate

### 8.1 recompute — REPLACE the block at server.py:884-895 (the comment lines 884-889, `pah_measured = False` :890, and the `derive_pah_compliance(..., enforced=False)` call :891-895) with:

```python
    # C9 (T1.4): PAH measurement is mandatory for closed kilns, resolved from
    # the project-year verification fetched above. Inert when the batch has no
    # project linkage or kiln_type isn't explicitly 'closed' (the deriver also
    # guards kiln-conditionality). enforced defaults to COMPLIANCE_ENFORCED —
    # the hardcoded enforced=False bypass is gone (was the only dead catalog
    # reason left after T1.2/T1.3).
    if batch.project_id and kiln_type == "closed":
        _pah_measured = bool(annual_verif and annual_verif.pah_measured)
        _pah_ok, _pah_reason = derive_pah_compliance(kiln_type, _pah_measured)
        if _pah_reason:
            c10_reasons.append(_pah_reason)
```

(Note `annual_verif` comes from the Phase-4 block — Phase 4 must land first. `kiln_type` is already in scope, resolved from telemetry earlier in recompute.)

### 8.2 Tests — same file (`test_annual_verification_c9.py`) or new `test_pah_gate.py`

To make `kiln_type == "closed"` true you must post telemetry carrying `kiln_type: "closed"` for the batch — copy the exact telemetry-payload shape from the existing C3b ignition tests (`grep -rn "kiln_type" backend/tests/ | grep closed` and reuse that helper; telemetry posts to `/api/v1/telemetry` and triggers recompute). Cases:
1. Closed-kiln + project-linked + verification with `pah_measured=None/False` → `missing_pah` present.
2. Closed-kiln + verification `pah_measured=true` → absent.
3. Closed-kiln + **no verification row at all** → present (`annual_verif is None` → `_pah_measured=False`).
4. **Open**-kiln, same setup as (1) → absent.
5. No project linkage, closed kiln → absent.
6. Regression: `grep -n "enforced=False" backend/server.py` → **zero hits** (add this as an actual test: read the source file and assert, mirroring how `test_transport_events_flow.py:48` asserts flag state — cheap and stops the bypass coming back).

**Gate → commit:** `fix(dmrv): remove hardcoded PAH bypass — closed-kiln PAH now gates issuance (Rainbow T1.4)`. Journal.

---

## 9. PHASE 6 — T1.9 + T1.10 closers (one commit)

### 9.1 T1.9 — lab biochar-moisture ≥ 3 samples

Locate the C7 lab request model used by `POST /api/v1/admin/lab` (server.py:660-715; the model defines `biochar_moisture_samples` / `biochar_moisture_samples_json` — grep `biochar_moisture` in server.py for the exact field name). Add a validator on that model (admin/lab channel — rejecting at the API is correct here, matching the `lab_h_corg ∈ [0.1,1.5]` precedent):

```python
    @field_validator("biochar_moisture_samples")
    @classmethod
    def _min_three_samples(cls, v):
        if v is not None and len(v) < 3:
            raise ValueError("moisture_samples_min_3: methodology requires >= 3 biochar moisture samples")
        return v
```

Tests in `test_lab_results_c7.py`: 2 samples → 422; 3 samples → 200; omitted (None) → 200 (field stays optional).

### 9.2 T1.10 — compliance-report provenance

In the compliance endpoint (server.py:2033-2073), enrich each checklist item with `enforcement`, so a verifier can distinguish "checked and passed" from "not applicable to this batch". Build a small resolver above the checklist comprehension:

```python
    # T1.10: per-item enforcement provenance. 'enforced' = the gate can fire
    # for this batch; 'inert_no_linkage' = needs project/scale linkage this
    # batch lacks; 'awaiting_methodology' = code path exists but is flag-gated
    # pending Rainbow sign-off (C6 transport).
    def _enforcement(code: str) -> str:
        if code == "transport_uncorroborated":
            return "enforced"  # GPS-derived check; the per-event fuel math is the flag-gated part
        if code in ("scale_calibration_expired",) and not batch.scale_id:
            return "inert_no_linkage"
        if code in ("missing_annual_methane", "missing_pah") and not batch.project_id:
            return "inert_no_linkage"
        if code == "attestation_unverified":
            return "awaiting_methodology" if not _ATTESTATION_ENFORCED else "enforced"
        return "enforced"
```

and add `"enforcement": _enforcement(code),` to the checklist dict (:2058-2066). Purely additive JSON — no client depends on this endpoint shape (admin-only).

Tests in `test_compliance_gate_c10.py`: linked batch → all three project-scoped codes report `"enforced"`; unlinked batch → they report `"inert_no_linkage"`; response still contains the original keys (back-compat).

**Gate → commit:** `feat(dmrv): lab moisture min-3 validation + compliance-report enforcement provenance (Rainbow T1.9/T1.10)`. Journal.

---

## 10. PHASE 7 — hygiene rider (optional, allowed, tiny)

Remove the bogus `@pytest.mark.asyncio` decorators from the three **sync** tests at `backend/tests/test_transport_events_flow.py:30, 36, 46` (kills 12 pytest warnings). Do NOT touch line 48's `assert TRANSPORT_EVENTS_ENFORCED is False` — that guard is load-bearing until T1.5. Commit: `chore(tests): drop asyncio marks from sync transport tests`.

---

## 11. DEFINITION OF DONE (the T1 exit benchmark)

Run and record in REMEDIATION_LOG.md:

1. `cd backend && python -m pytest -q` → **0 failed**, ≥ ~275 passed (262 baseline + your new tests).
2. `flutter analyze` → 25 issues, 0 errors (unchanged). `flutter test` → 0 failed (≥153).
3. `grep -n "enforced=False" backend/server.py` → **no matches**.
4. **Reachability proof:** one integration test (or three existing ones jointly) shows a project+scale-linked, closed-kiln batch with no calibration/verification carrying **exactly** `scale_calibration_expired`, `missing_annual_methane`, `missing_pah` among its reasons — and the same batch after admin posts (in-date calibration; verification `methane_run_count=3, pah_measured=true`) plus one evidence re-post shows **all three cleared**.
5. **Legacy invariance proof:** the Phase-1 legacy test — no-linkage payload produces none of the three reasons and byte-identical behavior otherwise.
6. Alembic: `alembic heads` shows single head `f1a2b3c4d5e6`; `upgrade head` + `downgrade -1` + `upgrade head` round-trips on a scratch SQLite file.
7. Client `schemaVersion == 23`; codegen committed (`app_database.g.dart` diff included); migration-shape test uses `greaterThanOrEqualTo`.
8. Five commits (+optional sixth), each with a journal entry, pushed.

**After this, the standing claim to Rainbow/verifiers becomes:** *every reason in the compliance catalog is reachable and tested; the only non-enforced criteria are the credit-math flips explicitly awaiting your annex numbers/sign-off (transport factors, methane→CH4, conversion factor, 1000-yr election), each behind a named flag.*

## 12. TRAPS — read before you start

- **Do not** make the new Pydantic fields `str` with defaults like `""` — must be `Optional[str] = None` (empty string would trip `min_length=1`).
- **Do not** add the reasons to `assemble()`'s keyword signature — they go through `extra_reasons` (that's the C10 pattern; the kwargs are for the pre-C10 signals only).
- **Recompute runs on every evidence post** — your gate lookups add up to 2 queries per recompute; that's accepted (matches the kiln-registry lookup pattern at :875-877). Don't "optimize" with module-level caches — recompute must stay pure per-call.
- **Order of DB effects in tests:** recompute happens at batch creation AND on each evidence post. If you post admin data (calibration/verification) *after* the batch exists, the batch's stored reasons are stale until the next evidence post re-triggers recompute. Tests must either post admin data first, or re-post evidence to refresh — assert accordingly (this mirrors how the existing C8 kiln tests are structured; check before writing).
- **`harvest_timestamp` naivety:** the plausibility check strips tzinfo (server.py:1148-1149) — for `.year` you're fine either way, but don't introduce tz-sensitive year math beyond `.year`.
- The `1 skipped` in the baseline is expected — leave it.
- If any existing test asserts the exact `BatchPayload` field set or the compliance-endpoint JSON shape (`test_endpoint_schemas.py`, `test_client_contract.py` are the likely places), run those FIRST after Phase 1/6 edits and extend them rather than fighting them.
