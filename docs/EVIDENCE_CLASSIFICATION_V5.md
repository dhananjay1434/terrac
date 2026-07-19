# EVIDENCE CLASSIFICATION V5 — Type Every Photo at the Source

## THE PROBLEM (one sentence)

Every photo a farmer captures is stored, hashed, GPS-stamped, and uploaded
correctly — but only the **burn/smoke** photos carry a `capture_type`, so the
**batch anchor photo** and the **farmer end-use application photo** land in the
portal's "Other / Uncategorized" bucket even though the app knows exactly what
they are.

## ROOT-CAUSE ANALYSIS (why this happens, verified in code)

The system has ONE field that drives evidence grouping in the portal:
`media_files.capture_type` (backend, `models.py:426`). The portal groups every
media item by it (`groupMedia` in `BatchDetail.tsx`); `null` → "Other".

There are **three ways** that field gets populated today, and they are
inconsistent:

| Media source | Enqueue site | capture_type at capture? | Result |
|---|---|---|---|
| Burn/smoke stages | `pyrolysis_screen.dart` → `insertMediaCaptureAndEnqueue(captureType:)` | **YES** — explicit, then re-verified by signed telemetry | Categorized + ✓ verified |
| Batch anchor photo | `biomass_sourcing` via generic `insertWithOutbox(photo_path)` | **NO** | "Other" until a backfill heuristic guesses it |
| Farmer end-use photo | `end_use_application` via `insertEndUseWithOutbox(farmer_photo_path)` | **NO** | "Other" — no heuristic covers it at all |

(KYC/enrollment are text-only — NOT a media source. Verified: no photo fields.)

**The architectural defect:** classification is *retrofitted downstream*
(a backfill script guessing from operation-id prefixes and hash matches,
`backend/scripts/backfill_media_capture_types.py`) instead of *asserted at the
source* where the type is known with certainty. The app knows a photo is a
farmer end-use photo the instant it's captured — that knowledge is thrown away
at the outbox boundary and a backend script later tries to reconstruct it.

## WHY THIS ARCHITECTURE IS THE RIGHT FIX (reasoned, non-biased)

The candidate fixes and why each alternative loses:

1. **Portal-only relabel / "re-tag" UI.** Rejected as the primary fix: the
   data is genuinely absent, so a human would have to re-classify every photo
   forever. Treats the symptom, scales inversely with volume (more farmers =
   more manual tagging), and puts classification in the least-authoritative
   place (a verifier guessing from a thumbnail) instead of the most (the app
   that took the photo). Keep a *manual override* as a fallback (Phase 4), not
   the fix.

2. **Backend backfill only.** Rejected: heuristics (op-id prefix, hash ==
   batch anchor) are guesses that will silently mis-file or miss new media
   types. A backfill is correct for *legacy rows already in the DB* (Phase 3),
   but making it the ongoing mechanism means every new capture type needs a new
   guess-rule. Guessing is not a source of truth.

3. **Type at the source, carry it end-to-end (CHOSEN).** The capture screen is
   the only place that knows, with zero ambiguity, what a photo is. Stamp
   `capture_type` there, thread it through the existing outbox→sync→upload
   pipeline (which *already* forwards `payload['capture_type']` as the
   `X-Capture-Type` header — no new plumbing), store it, display it. Every
   layer already has the field; two enqueue sites just fail to populate it.
   This is additive, not a rewrite; it scales (new media type = one constant in
   one vocabulary, consumed everywhere); and it puts truth at the source.

**The unifying principle:** introduce ONE controlled vocabulary of capture
types, defined once, referenced everywhere (app enum, backend validator,
portal titles). Today the "vocabulary" is implicit and duplicated as loose
strings in three languages. V5 makes it explicit and the single source of
truth, so "Other / Uncategorized" becomes a genuine exception (truly unknown
media) rather than the default dumping ground.

## THE CANONICAL VOCABULARY (define once, in this order)

The evidence-step order the portal already implies, made complete and explicit:

```
batch_photo          → "Batch photo"                    (biomass anchor)
flame_curtain        → "Burn — flame curtain"           (existing)
quenching            → "Burn — quenching"               (existing)
flame_height         → "Burn — flame height"            (existing)
smoke_0 / smoke_50 / smoke_90 / smoke_100  → "Smoke opacity — N%"  (existing)
post_burn_mass       → "Post-burn mass"                 (already in titles)
packaging            → "Packaging"                      (already in titles)
end_use              → "End use — field application"     (NEW — farmer photo)
lab_certificate      → "Lab certificate"                (existing)
```

`end_use` is the one genuinely new type. `batch_photo` already exists in the
vocabulary but is only reached via backfill — V5 stamps it at capture instead.

## SCOPE — this spans three layers. Nothing else changes.

- **App (Flutter, `lib/`):** populate `capture_type` at the two enqueue sites
  that omit it. No new screens, no capture-flow changes, no schema change (the
  value rides in the existing outbox `payload_json`).
- **Backend (Python, `backend/`):** the validator already accepts any
  `^[a-z0-9_]{1,64}$` — `end_use` passes as-is; no endpoint change. Extend the
  backfill to reclassify legacy `end_use` / anchor rows. Add tests.
- **Portal (React, `portal/`):** add the new type(s) to `STEP_ORDER` +
  `STEP_TITLES` so they render as named, ordered sections. Tests.

## HARD RULES (all layers)

1. **No new network calls, no changed payload/response shapes, no schema
   migrations.** `capture_type` is an existing column and an existing header.
   You are populating an existing field, not adding one.
2. **The signed-telemetry trust model is untouched.** `capture_type_verified`
   still flips true ONLY via `label_media_from_telemetry`. Source-stamped types
   on non-burn media (batch_photo, end_use) are UNVERIFIED hints — exactly like
   the existing client hint for burn photos. Do not mark them verified.
3. **Controlled vocabulary is the contract.** Every capture_type string an app
   enqueues must be in the canonical list above. No ad-hoc strings.
4. Gate every phase with that layer's full test suite; one commit per phase; do
   NOT push.
5. Read every target file verbatim before editing. Match exactly.
6. Do not "improve" adjacent code. Surgical, additive changes only.

---

## PHASE 1 — App: stamp `capture_type` at the two untyped enqueue sites

Files: `lib/data/local/yield_end_use_writers.dart`,
and the biomass-sourcing writer (LOCATE it first: grep
`lib/data/local` for the writer that inserts `targetTable: 'biomass_sourcing'`
with a `photo_path` — read it verbatim before editing).

### 1a. Define the vocabulary as a single Dart constant

Create `lib/data/capture_types.dart` (new file) with a canonical enum/const map
so no screen hard-codes a loose string:

```dart
/// The single source of truth for evidence capture-type labels. Every media
/// row enqueued for /media upload MUST use one of these — the backend stores
/// it verbatim and the verifier portal groups evidence by it. Adding a new
/// evidence kind = one entry here, consumed everywhere.
class CaptureType {
  static const batchPhoto = 'batch_photo';
  static const flameCurtain = 'flame_curtain';
  static const quenching = 'quenching';
  static const flameHeight = 'flame_height';
  static const postBurnMass = 'post_burn_mass';
  static const packaging = 'packaging';
  static const endUse = 'end_use';
  static const labCertificate = 'lab_certificate';
  // smoke_0 / smoke_50 / smoke_90 / smoke_100 are produced dynamically by the
  // pyrolysis smoke-stage flow and are already stamped there.
}
```

### 1b. End-use farmer photo

In `insertEndUseWithOutbox` (`yield_end_use_writers.dart`), add
`'capture_type': CaptureType.endUse` to the `payload` map (import the new
constant). Do NOT touch the companion/DB row — only the outbox payload the
sync manager reads. The sync manager already forwards
`payload['capture_type']` as `X-Capture-Type` (verified:
`sync_queue_manager.dart:565`).

### 1c. Batch anchor photo

In the biomass-sourcing writer, add `'capture_type': CaptureType.batchPhoto`
to its outbox payload the same way.

### 1d. Refactor pyrolysis to use the constant (consistency, no behavior change)

In `pyrolysis_screen.dart`, replace the literal flame/stage strings passed to
`_captureStage(...)` with `CaptureType.*` constants where they map 1:1
(`flame_curtain`, `quenching`, `flame_height`). Leave the dynamic `smoke_N`
strings as-is (they're computed). This makes the vocabulary single-sourced.
Verify the resulting strings are byte-identical to today's — this is a
readability refactor, NOT a value change.

**App tests:** run `flutter test`. Add/extend a writer test asserting the
end-use and biomass outbox payloads now contain the correct `capture_type`.
LOCATE the existing writer tests first (grep `test/` for `insertEndUseWithOutbox`
/ `insertWithOutbox`); mirror their style. All existing tests pass unchanged.

**Commit:** `feat(app): stamp capture_type at source for batch-anchor and farmer end-use photos`

---

## PHASE 2 — Portal: render the new types as named sections

Files: `portal/src/pages/BatchDetail.tsx` (`STEP_ORDER`, `STEP_TITLES`),
`portal/src/components/EvidenceGallery/EvidenceGallery.test.tsx`,
`portal/src/pages/__tests__/BatchDetail.test.tsx`.

### 2a. Extend the vocabulary

In `BatchDetail.tsx`, add `end_use` to `STEP_ORDER` in its correct position
(after `packaging`, before `lab_certificate`) and add to `STEP_TITLES`:

```
end_use: "End use — field application",
```

Confirm `batch_photo`, `post_burn_mass`, `packaging` are already present (they
are) so a source-stamped `batch_photo` now sorts into its real slot at the top
instead of "Other".

### 2b. Keep "Other" as a true exception

Do NOT remove the `__unclassified__` bucket — it must remain for genuinely
unknown/legacy media. After this change it should be rare, not the default.

**Portal tests:** extend `EvidenceGallery.test.tsx` — add an `end_use` item to
the fixture and assert it renders under "End use — field application", NOT
"Other". Full portal gate: `npm test -- --run`, `npm run typecheck`,
`npm run build`. Existing evidence/batch tests pass unchanged.

**Commit:** `feat(portal): render end-use + batch-anchor evidence as named sections`

---

## PHASE 3 — Backend: reclassify legacy rows + lock the vocabulary in a test

Files: `backend/scripts/backfill_media_capture_types.py`,
`backend/tests/test_backfill_media_capture_types.py`,
`backend/tests/test_media_capture_type.py`.

### 3a. Backfill for end-use (legacy rows already in the DB)

Legacy `end_use` photos predate the app fix and are still NULL. Add a rule to
the backfill: media rows joined to an `end_use_application` whose
`farmer_photo_sha256 == media.sha256_hash` → `capture_type = 'end_use'`,
`capture_type_verified = False` (source hint, not telemetry-verified). LOCATE
the end_use model + its farmer_photo_sha256 column first; mirror the existing
`batch_photo`-by-hash rule already in the script (lines ~53-58).

### 3b. Vocabulary regression test

Add a test asserting the backend accepts every canonical type
(`end_use`, `batch_photo`, …) via the `X-Capture-Type` validator, and that the
backfill assigns `end_use` correctly with `verified=False`. This locks the
contract so a future change can't silently drop a type.

**Backend tests:** `pytest backend/tests/` (or the repo's documented runner).
All existing tests pass; new ones green.

**Commit:** `feat(backend): backfill legacy farmer end-use photos to capture_type=end_use`

---

## PHASE 4 (OPTIONAL — only if the user wants a human fallback)

A verifier-facing manual re-tag control in the portal for anything STILL in
"Other" (truly unknown media). Requires a NEW authenticated backend endpoint
(`PATCH media/{id}/capture-type`) writing `verified=False, source=manual`.
This is a real feature, not a bug fix — DO NOT build it unless explicitly
asked. Documented here so the architecture leaves room for it (the vocabulary
and unverified-hint model already support it).

---

## FINAL ACCEPTANCE

1. All three layers' test suites green (Flutter, pytest, vitest).
2. A freshly captured batch: farmer end-use photo appears under "End use —
   field application" and the anchor photo under "Batch photo" — neither in
   "Other". (Reason through the data flow in the final report; no live device
   needed.)
3. Legacy batches: after backfill --apply, existing end-use photos reclassify.
4. "Other / Uncategorized" still exists and is now genuinely rare.
5. `capture_type_verified` semantics unchanged — only telemetry verifies.
6. Zero schema migrations, zero changed API shapes, zero new network calls
   (except the explicitly-optional Phase 4). Nothing pushed.

## WHY THIS IS SCALABLE, NOT A QUICK FIX (closing rationale)

- **Truth at the source:** the app stamps what it knows; nothing downstream
  guesses. New evidence kinds cost one vocabulary entry, not a new heuristic.
- **One vocabulary, three consumers:** app enum → backend validator → portal
  titles. A single list is the contract; drift is caught by the Phase 3 test.
- **The pipeline was already built for this:** outbox → sync → `X-Capture-Type`
  → column → `groupMedia` all exist and forward the field. V5 only fills the
  two gaps where it was dropped — minimal blast radius, maximal coverage.
- **"Other" becomes meaningful:** it stops being the default and becomes a real
  signal ("this media is genuinely unclassified") worth a human's attention —
  which is exactly what the optional Phase 4 manual override is for.
