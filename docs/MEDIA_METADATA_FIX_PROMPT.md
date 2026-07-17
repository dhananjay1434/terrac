# MEDIA METADATA FIX PROMPT — anchor evidence photos to their capture step

> Copy everything below the line into the agent. Repo root:
> `c:\Users\bit\Downloads\flutter_dmrv_full (1)\flutter_dmrv`. Python 3.11 +
> backend requirements installed; Flutter SDK for the mobile phases. The agent
> must do the phases IN ORDER, ONE AT A TIME, and STOP when a CHECK fails.

---

You are fixing a data-model gap in a biochar dMRV system (FastAPI backend +
Flutter field app + React portal). Trust ONLY the source code, not .md docs.

## THE PROBLEM (verified in code — read these call sites first)

Evidence photos reach the server as anonymous bytes. The backend cannot tell
whether a stored photo is a flame-curtain shot, a quenching shot, a smoke
opacity proof, a moisture sample, or the farmer's batch photo:

1. **The app KNOWS the step at capture time and stores it locally.**
   `lib/data/local/pyrolysis_writer.dart` `insertMediaCaptureAndEnqueue`
   (lines ~22–67) writes a local `media_captures` row with `captureType`
   (values like `smoke_0/smoke_50/smoke_90/smoke_100`, `flame_curtain`,
   `quenching`, `flame_height`) and enqueues a SyncOutbox row with
   `targetTable: 'media'` whose `payload_json` contains
   `{photo_path, sha256_hash, capture_type, batch_uuid, isMockLocation}`.

2. **The sync loop then throws the metadata away.**
   `lib/services/sync_queue_manager.dart` `_processEntry` (~line 448):
   `if (entry.targetTable == 'media')` → *"skipping JSON metadata Phase 1"* —
   only the multipart blob is uploaded by `_uploadMedia` (~lines 632–714) with
   headers `X-Idempotency-Key` (= `<outbox-uuid>_media`, a random UUID),
   `X-Device-Id`, `X-Mock-Location`, `X-Batch-UUID`, `X-Declared-SHA256`,
   `X-Signature`. **`capture_type` is never sent.**

3. **The server has nowhere to put it anyway.**
   `backend/models.py` `MediaFile` (~lines 396–424) has NO step/kind column:
   only `batch_uuid, operation_id, file_path, sha256_hash, filename,
   exif_lat, exif_lon, uploaded_at`. `backend/routers/media.py upload_media`
   reads no metadata field.

4. **The ONLY existing linkage is indirect.** The telemetry payload
   (`pyrolysis_writer.dart` ~lines 108–115) carries
   `smoke_evidence: [{stage, sha256}]` (stage = captureType with the `smoke_`
   prefix stripped, so `'0'/'50'/'90'/'100'`, and the flame stages verbatim).
   The server stores it opaquely in `pyrolysis_telemetry.payload_json`
   (`backend/routers/evidence.py create_telemetry` ~lines 91–117) and
   `backend/corroboration.py derive_pyrolysis_photo_compliance` (~145–167)
   reads the stage set for the Rainbow C3 gate — but **no media_files row is
   ever labeled**, and non-burn media (batch photo, lab certificates) have no
   linkage at all.

## THE DESIGN (do not deviate)

- Add `capture_type` (String(64), nullable) + `capture_type_verified`
  (Boolean, default False) to `media_files`, via Alembic.
- Accept an OPTIONAL `X-Capture-Type` header on `POST /api/v1/media`.
  **Do NOT touch the Ed25519 media canonical** (`security.py`
  `verify_media_signature`) — it is frozen; changing it bricks deployed
  clients. The header is therefore a client-authored HINT
  (`capture_type_verified=False`).
- The AUTHORITATIVE label comes from server-side corroboration: the telemetry
  payload is Ed25519-signed by the device, and its `smoke_evidence[].sha256`
  values identify photos. When telemetry lands, stamp matching media rows
  (`batch_uuid` + `sha256_hash`) with the stage and set
  `capture_type_verified=True`. The same pass runs on media upload (media can
  arrive after telemetry — deferred anchoring is a real flow).
- Backfill historical rows with a one-off admin script using the same rule.
- Only then teach the app to send the header, and the portal/export to show it.

## GLOBAL RULES — apply to every phase

1. **One phase at a time.** Finish phase N (code + tests + full suite green +
   commit) before you even READ phase N+1.
2. **Never claim a test passed without running it and seeing the output.**
3. Backend commands run from
   `cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/backend"`.
   Full-suite gate after every backend phase: `python -m pytest -q` —
   baseline is the current count on your start commit (record it in Phase 0),
   0 failed afterward.
4. Flutter checks run from the repo root: `flutter analyze` must report no
   NEW issues, and `flutter test` must stay green.
5. One phase = one commit, exact message given. Stage ONLY the files the
   phase names.
6. No refactors, no renames, no drive-by fixes. Line numbers may have
   drifted — locate the verbatim code shown before editing.
7. Test conventions (verified in `backend/tests/conftest.py`): `client` =
   SignedAsyncClient over in-memory SQLite; `session_factory` fixture; admin
   header `{"X-Admin-Secret": "test-admin-secret"}`; JSON bodies via
   `content=json.dumps(p).encode("utf-8")`; media uploads need explicit
   `X-Signature` — copy the header pattern from
   `backend/tests/test_media_auth.py` (`sign_media(device, op, sha, bu)` from
   `tests.remediation.crypto_utils`, `DEVICE = "test-device-reg"`, fixtures
   `client, registered_device`).

---

<!-- PHASE0 -->
# PHASE 0 — baseline

```bash
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/backend"
python -m pytest -q          # record "N passed, M skipped" — this is your gate
git log --oneline -3         # record the start commit
```
No commit. STOP if anything fails — report and wait.

<!-- PHASE1 -->
# PHASE 1 — backend: column + optional header (backward compatible)

**Files:** `backend/models.py`, new Alembic revision under
`backend/alembic/versions/`, `backend/routers/media.py`, new test
`backend/tests/test_media_capture_type.py`.

Step 1a — `backend/models.py`, inside `class MediaFile` immediately after the
`exif_lon` column:

```python
    # Evidence-step label. `capture_type` arrives as an OPTIONAL client hint
    # (X-Capture-Type header — NOT in the frozen media canonical, so unsigned);
    # `capture_type_verified` flips True only when the server corroborates the
    # label against the Ed25519-signed telemetry smoke_evidence (stage, sha256)
    # pairs. NULL = legacy row or non-burn media not yet classified.
    capture_type: Mapped[str] = mapped_column(String(64), nullable=True)
    capture_type_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
```

(`Boolean` is already imported in models.py — verify; add to the existing
sqlalchemy import if not.)

Step 1b — new Alembic revision. Copy the STYLE of
`backend/alembic/versions/b2c3d4e5f6a7_media_add_exif_gps.py` (read it first —
it did exactly this kind of additive media_files change). Set
`down_revision` to the CURRENT head — find it with:

```bash
python -m alembic heads    # from backend/, or read the newest file's revision id
```

Upgrade adds both columns (`sa.String(64)` nullable, `sa.Boolean` non-null
`server_default=sa.false()`); downgrade drops them.

Step 1c — `backend/routers/media.py` `upload_media`: add the header param
after `x_device_id`:

```python
    x_capture_type: Optional[str] = Header(None, alias="X-Capture-Type"),
```

Validate right after the X-Declared-SHA256 length check:

```python
    if x_capture_type is not None and not re.match(
        r"^[a-z0-9_]{1,64}$", x_capture_type
    ):
        raise HTTPException(status_code=400, detail="invalid_capture_type")
```

And set it on the MediaFile constructor (`capture_type=x_capture_type` — the
verified flag stays False here).

Step 1d — new test `backend/tests/test_media_capture_type.py`, following the
signing pattern of `test_media_auth.py` exactly (fixtures
`client, registered_device`; `sign_media`; `DEVICE = "test-device-reg"`):
- upload WITH `X-Capture-Type: flame_curtain` → 200; row has
  `capture_type == "flame_curtain"` and `capture_type_verified is False`
- upload WITHOUT the header → 200; `capture_type is None` (legacy clients
  unaffected)
- upload with `X-Capture-Type: "Fla me!"` → 400 `invalid_capture_type`
  (and, per audit fix 3, assert NO media row was left behind)

**CHECKS:**
```bash
python -m pytest tests/test_media_capture_type.py tests/test_media_auth.py tests/test_media_poisoned_row.py -q
python -m pytest -q     # >= Phase-0 baseline, 0 failed
```

**Commit:** `feat(media): capture_type column + optional X-Capture-Type hint header`

<!-- PHASE2 -->
# PHASE 2 — backend: authoritative labeling from signed telemetry

**Files:** `backend/services/evidence.py` (new helper),
`backend/routers/evidence.py` (call it from `create_telemetry`),
`backend/routers/media.py` (call it on upload), new test
`backend/tests/test_media_capture_type_verify.py`.

Step 2a — add to `backend/services/evidence.py`:

```python
async def label_media_from_telemetry(
    session, batch_uuid: str, smoke_evidence: list | None
) -> int:
    """Stamp media_files.capture_type from the Ed25519-signed telemetry
    smoke_evidence [{stage, sha256}] pairs (batch_uuid + sha256 match).
    The signed telemetry is the trust root, so the label is marked verified —
    it OVERWRITES any unverified client hint. Returns rows updated.
    Idempotent; safe to call on every telemetry POST and media upload."""
    from models import MediaFile
    from sqlalchemy import select

    updated = 0
    for e in smoke_evidence or []:
        if not isinstance(e, dict):
            continue
        stage, sha = e.get("stage"), e.get("sha256")
        if not stage or not sha:
            continue
        rows = (
            await session.execute(
                select(MediaFile).where(
                    MediaFile.batch_uuid == batch_uuid,
                    MediaFile.sha256_hash == str(sha).lower(),
                )
            )
        ).scalars().all()
        for m in rows:
            if not m.capture_type_verified:
                m.capture_type = str(stage)[:64]
                m.capture_type_verified = True
                session.add(m)
                updated += 1
    return updated
```

NOTE the stage vocabulary: the app strips the `smoke_` prefix before it
builds smoke_evidence (`pyrolysis_writer.dart` ~line 111), so verified labels
are `'0'/'50'/'90'/'100'` for opacity proofs and
`flame_curtain/quenching/flame_height` verbatim. STORE THEM AS-IS — do not
invent a new taxonomy; the portal can prettify.

Step 2b — `backend/routers/evidence.py` `create_telemetry`: after the
successful commit AND inside the `_upsert_one_to_one_evidence` duplicate path
(read that helper first — call it after the upsert commit too, from
`create_telemetry` itself), run:

```python
    n = await label_media_from_telemetry(
        session, payload.batch_uuid, payload.smoke_evidence
    )
    if n:
        await session.commit()
```

Step 2c — `backend/routers/media.py`: media can arrive AFTER telemetry.
Inside `upload_media`'s existing `try:` block, after `_evaluate_anchor` /
before the final commit, look up the batch's telemetry row
(`select(PyrolysisTelemetry).where(PyrolysisTelemetry.batch_uuid == batch_uuid)`,
import the model), parse its `payload_json`, and call
`label_media_from_telemetry(session, batch_uuid, parsed.get("smoke_evidence"))`.
Wrap the json.loads in try/except (ValueError, TypeError) → skip. The final
commit already in the handler persists it.

Step 2d — new test `backend/tests/test_media_capture_type_verify.py`:
- **telemetry-then-media**: POST telemetry (copy a passing telemetry payload
  from an existing test — grep `"/api/v1/telemetry"` under `backend/tests/`)
  whose smoke_evidence contains the photo's sha256 with stage
  `flame_curtain`; then upload that photo with NO X-Capture-Type header →
  row ends with `capture_type == "flame_curtain"`,
  `capture_type_verified is True`.
- **media-then-telemetry**: upload first (row unverified/NULL), then POST
  telemetry → row flips to verified with the stage.
- **hint vs signed truth**: upload with a LYING header
  (`X-Capture-Type: quenching`) then telemetry says `flame_curtain` →
  verified label wins (`flame_curtain`, verified True).

**CHECKS:**
```bash
python -m pytest tests/test_media_capture_type_verify.py tests/test_media_capture_type.py tests/test_corroboration.py -q
python -m pytest -q     # >= baseline, 0 failed
```

**Commit:** `feat(media): verify capture_type against signed telemetry smoke_evidence`

<!-- PHASE3 -->
# PHASE 3 — backend: backfill historical rows (one-off admin script)

**Files:** new `backend/scripts/backfill_media_capture_types.py`, new test
`backend/tests/test_backfill_media_capture_types.py`.

Write an idempotent script (async, reuses `db.get_engine`/session patterns —
copy the bootstrap from an existing script under `backend/scripts/` if one
exists; otherwise build a minimal `async_sessionmaker` from `db.py`'s engine)
that labels EXISTING `media_files` rows, in this priority order:

1. **Telemetry rule (verified):** for every `pyrolysis_telemetry` row, parse
   `payload_json` → `smoke_evidence` and call the SAME
   `label_media_from_telemetry` helper from Phase 2. Never duplicate the
   logic.
2. **Lab certificates (verified):** rows whose `operation_id` starts with
   `labcert-` (the portal lab-certificate route uses this prefix — verify by
   grepping `labcert` in `backend/portal/routes.py`) → `capture_type =
   "lab_certificate"`, verified True (the row was created by an
   authenticated portal upload).
3. **Batch anchor photo (verified):** rows whose `sha256_hash` equals their
   batch's `batches.sha256_hash` → `capture_type = "batch_photo"`, verified
   True (the batch payload that declared this hash was Ed25519-signed).
4. Everything else stays NULL — print a count, do not guess.

The script must: take `--dry-run` (default) vs `--apply`; print per-rule
counts; never downgrade an already-verified label.

Test: seed a media row + telemetry row + a labcert- row + a batch-photo row
in SQLite via `session_factory`, run the script's labeling function
in-process (import it — design the script so the core is an importable
`async def backfill(session) -> dict` and the CLI is a thin wrapper), assert
all four outcomes.

**CHECKS:**
```bash
python -m pytest tests/test_backfill_media_capture_types.py -q
python -m pytest -q     # >= baseline, 0 failed
python scripts/backfill_media_capture_types.py --dry-run   # runs, prints counts
```

**Commit:** `feat(media): backfill script labeling historical media from signed evidence`

<!-- PHASE4 -->
# PHASE 4 — mobile app: send the label going forward

**Files:** `lib/services/sync_queue_manager.dart` only.

In `_uploadMedia` (~lines 632–714), the caller `_processEntry` already
decodes `entry.payloadJson` (~line 527) and reads `payload['capture_type']`
into a debug print (~line 543). Thread it through: add an optional
`String? captureType` parameter to `_uploadMedia`, pass
`payload['capture_type'] as String?` at the call site (~line 558), and set
the header just after `X-Batch-UUID`:

```dart
    if (captureType != null && captureType.isNotEmpty) {
      request.headers['X-Capture-Type'] = captureType;
    }
```

Do NOT touch `signMediaUpload` or its inputs — the media canonical is frozen;
the server treats the header as a hint until telemetry corroborates it.
Batch-photo uploads (rows whose payload has `photo_path`/`sha256_hash` but no
`capture_type`) simply send no header — the Phase 3 batch-anchor rule labels
them server-side.

**CHECKS:**
```bash
flutter analyze              # no NEW issues in sync_queue_manager.dart
flutter test                 # stays green
```
If there is an existing sync-queue unit test (grep `sync_queue` under
`test/`), extend it to assert the header is present when the outbox payload
carries capture_type; if none exists, note that in the report — do NOT build
a new harness.

**Commit:** `feat(app): send X-Capture-Type with evidence media uploads`

<!-- PHASE5 -->
# PHASE 5 — portal: SEGREGATED evidence gallery (grouped by step, with GPS + metadata)

**Files:** `backend/portal/routes.py` (batch_detail media projection), new test
assertions in the portal batch-detail test (grep `batch_detail` or
`"/api/v1/portal/batches/"` under `backend/tests/` to find it),
`portal/src/api.ts` (MediaItem type), `portal/src/pages/BatchDetail.tsx`
(grouped gallery), `portal/src/__tests__/` (extend existing test file only).

## 5a — backend: enrich the media projection

`backend/portal/routes.py` `batch_detail` currently projects (VERIFIED at
~lines 291–306 — locate this verbatim block):

```python
    media_rows = (
        await session.execute(
            select(MediaFile)
            .where(MediaFile.batch_uuid == buid)
            .order_by(MediaFile.uploaded_at.asc())
        )
    ).scalars().all()
    media = [
        {
            "operation_id": m.operation_id,
            "filename": m.filename,
            "sha256_hash": m.sha256_hash,
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
        }
        for m in media_rows
    ]
```

Replace the list-comp dict with (everything else in the handler untouched):

```python
    media = [
        {
            "operation_id": m.operation_id,
            "filename": m.filename,
            "sha256_hash": m.sha256_hash,
            "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            # Phase 1/2 labeling: step + whether signed telemetry corroborated it.
            "capture_type": m.capture_type,
            "capture_type_verified": bool(m.capture_type_verified),
            # EXIF GPS parsed at upload time (NULL when the photo had none).
            "exif_lat": m.exif_lat,
            "exif_lon": m.exif_lon,
        }
        for m in media_rows
    ]
```

Do NOT group server-side — the portal groups; the API stays a flat list
(exports and other consumers want the flat manifest).

Extend the existing portal batch-detail test: seed one MediaFile with
`capture_type="flame_curtain", capture_type_verified=True, exif_lat=10.5,
exif_lon=20.5` and assert those four keys round-trip in the JSON.

## 5b — portal types

`portal/src/api.ts` — the interface is currently (VERIFIED lines 45–50):

```ts
export interface MediaItem {
  operation_id: string;
  filename: string | null;
  sha256_hash: string;
  uploaded_at: string | null;
}
```

Extend it (additive only):

```ts
export interface MediaItem {
  operation_id: string;
  filename: string | null;
  sha256_hash: string;
  uploaded_at: string | null;
  capture_type: string | null;
  capture_type_verified: boolean;
  exif_lat: number | null;
  exif_lon: number | null;
}
```

## 5c — portal UI: grouped gallery

`portal/src/pages/BatchDetail.tsx` currently renders one flat grid
(VERIFIED ~lines 189–198):

```tsx
      {d.media.length > 0 && (
        <section className="card" style={{ marginTop: 14 }}>
          <span className="micro">Evidence media</span>
          <div className="media-grid">
            {d.media.map((m) => (
              <MediaThumb key={m.operation_id} item={m} />
            ))}
          </div>
        </section>
      )}
```

Replace with a gallery grouped by step. Group order and display names are
FIXED — use exactly this table (`capture_type` values come from the app's
vocabulary; `'0'/'50'/'90'/'100'` are telemetry-verified smoke stages with
the `smoke_` prefix stripped):

| group key(s) | display title |
|---|---|
| `batch_photo` | Batch photo |
| `flame_curtain` | Burn — flame curtain |
| `quenching` | Burn — quenching |
| `flame_height` | Burn — flame height |
| `smoke_0`, `0` | Smoke opacity — 0% |
| `smoke_50`, `50` | Smoke opacity — 50% |
| `smoke_90`, `90` | Smoke opacity — 90% |
| `smoke_100`, `100` | Smoke opacity — 100% |
| `lab_certificate` | Lab certificate |
| anything else non-null | its raw value |
| `null` | Unclassified |

Implementation (adapt to the file's existing style; keep `MediaThumb`):

```tsx
const STEP_TITLES: Record<string, string> = {
  batch_photo: "Batch photo",
  flame_curtain: "Burn — flame curtain",
  quenching: "Burn — quenching",
  flame_height: "Burn — flame height",
  smoke_0: "Smoke opacity — 0%", "0": "Smoke opacity — 0%",
  smoke_50: "Smoke opacity — 50%", "50": "Smoke opacity — 50%",
  smoke_90: "Smoke opacity — 90%", "90": "Smoke opacity — 90%",
  smoke_100: "Smoke opacity — 100%", "100": "Smoke opacity — 100%",
  lab_certificate: "Lab certificate",
};
const STEP_ORDER = [
  "batch_photo", "flame_curtain", "quenching", "flame_height",
  "smoke_0", "0", "smoke_50", "50", "smoke_90", "90", "smoke_100", "100",
  "lab_certificate",
];

function groupMedia(items: MediaItem[]): [string, MediaItem[]][] {
  const groups = new Map<string, MediaItem[]>();
  for (const m of items) {
    const k = m.capture_type ?? "__unclassified__";
    (groups.get(k) ?? groups.set(k, []).get(k)!).push(m);
  }
  const keys = [...groups.keys()].sort((a, b) => {
    const ia = STEP_ORDER.indexOf(a), ib = STEP_ORDER.indexOf(b);
    if (a === "__unclassified__") return 1;
    if (b === "__unclassified__") return -1;
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
  return keys.map((k) => [k, groups.get(k)!]);
}
```

Render one sub-section per group: title =
`STEP_TITLES[key] ?? (key === "__unclassified__" ? "Unclassified" : key)`,
count badge, then the existing `media-grid` of `MediaThumb`s.

Upgrade `MediaThumb`'s caption (currently just the hash prefix, VERIFIED
line 50: `{item.sha256_hash.slice(0, 12)}…`) to a small metadata block:
- hash prefix (keep)
- upload time: `item.uploaded_at?.slice(0, 16).replace("T", " ")`
- GPS line ONLY when present:
  `📍 {item.exif_lat.toFixed(5)}, {item.exif_lon.toFixed(5)}` as a link to
  `https://www.openstreetmap.org/?mlat=${lat}&mlon=${lon}#map=17/${lat}/${lon}`
  (target `_blank`, `rel="noreferrer"`); when absent render the muted text
  `no GPS`
- a `✓ verified` chip when `capture_type_verified`, `unverified` (muted)
  when a label exists but is not corroborated, nothing when unclassified

Keep styles consistent with the existing `.cap`/`.micro` classes — no new CSS
framework, no new dependencies. NO map widget; the OSM link is enough.

## 5d — portal test

Extend the EXISTING test file under `portal/src/__tests__/` (do not create a
new harness): a unit test for `groupMedia` — given 4 items
(`flame_curtain`, `"0"`, `null`, `flame_curtain`) it returns groups in
STEP_ORDER with unclassified last and preserves item order within a group.
Export `groupMedia` from the component file to make it testable.

**CHECKS:**
```bash
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/backend" && python -m pytest -q   # >= baseline, 0 failed
cd "c:/Users/bit/Downloads/flutter_dmrv_full (1)/flutter_dmrv/portal" && npm test -- --run       # all green
```

**Commit:** `feat(portal): evidence gallery grouped by capture step with GPS + verification badges`

<!-- PHASE6 -->
# PHASE 6 — export: evidence manifest in registry reports

**Files:** `backend/services/export.py`, extend
`backend/tests/test_export_endpoints.py`.

In `export_batch_common` (read it first — it already loads child payloads via
`_load_child_payloads`), after the `transport` load, add:

```python
    media_rows = (
        await session.execute(
            select(MediaFile).where(MediaFile.batch_uuid == batch.batch_uuid)
        )
    ).scalars().all()
```

(import `MediaFile` in the existing `from models import ...` line) and add to
the returned dict, after `"transport_events"`:

```python
        "evidence_media": [
            {
                "operation_id": m.operation_id,
                "sha256_hash": m.sha256_hash,
                "capture_type": m.capture_type,
                "capture_type_verified": bool(m.capture_type_verified),
                "exif_lat": m.exif_lat,
                "exif_lon": m.exif_lon,
                "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            }
            for m in media_rows
        ],
```

Test: in `test_export_endpoints.py`, extend `test_csi_export_ok` (or add one
test) — seed a MediaFile row for the batch with a verified capture_type and
assert `body["evidence_media"][0]["capture_type"] == "flame_curtain"` and
`["capture_type_verified"] is True`.

**CHECKS:**
```bash
python -m pytest tests/test_export_endpoints.py tests/test_portal_export.py -q
python -m pytest -q     # >= baseline, 0 failed
```

**Commit:** `feat(export): evidence_media manifest with step labels in registry reports`


<!-- WRAPUP -->
# FINAL WRAP-UP

1. Full backend suite one more time — paste the tail. Expected: Phase-0
   baseline + all new tests, 0 failed.
2. `git log --oneline -9` — expected: 6 commits in phase order.
3. Report per phase: files touched, tests added, counts, anything adapted
   (drifted line numbers, missing test seams) explicitly.
4. Do NOT push. The human reviews, pushes, and redeploys Render (the
   Alembic migration runs at startup via the lifespan `init_db`).

## Explicitly OUT OF SCOPE (do not attempt)
- Changing the Ed25519 media canonical (would brick deployed clients).
- Renaming the `'0'/'50'/'90'/'100'` stage vocabulary.
- Retroactively marking unlabeled legacy media as failed/invalid.
- Any compliance-gate change in `corroboration.py` — C3 already works off
  telemetry; this migration only makes the media rows self-describing.
- Switching media storage to S3 / persistent disk (separate post-demo task —
  the "unavailable" thumbnails are ephemeral-disk loss, NOT a labeling bug).
- Map widgets or new frontend dependencies — the OSM link is the map.

