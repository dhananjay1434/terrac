# Post-refactor fixup SOP (F1–F8)

> Context: R1–R10 (the server.py strangler-fig refactor) are ALL committed. This SOP fixes
> issues found in the post-R10 brutal audit. **These are surgical, independent fixes** — not a
> continuation of the extraction. Each step below is self-contained: read it, make ONLY the
> exact edit(s) it describes, run its gate, commit, move to the next step. **Do not touch any
> file not named in the step you are executing. Do not "clean up" anything you notice along the
> way — file it as a new step instead of improvising.**

## Ground rules (same discipline as the R1–R10 SOP)

1. **One step = one commit.** Never combine two F-steps into one commit.
2. **Read the step fully before editing anything.** Every edit below gives you the exact
   current text and the exact replacement text. If the file on disk does not match the "Current"
   block byte-for-byte (modulo whitespace), STOP and report the mismatch — do not guess.
3. **Every step ends with the SAME gate** unless the step says otherwise:
   ```
   cd backend
   DMRV_DISABLE_DOTENV=1 python -m pytest -q
   ```
   Expected: **416 passed, 2 skipped**. If the number differs, STOP — do not commit, report what
   changed.
4. Steps are ordered by risk (cosmetic/hygiene first is NOT the order — bug fixes come first,
   then behavioral fixes, then hygiene, then cosmetic). Do them in order: F1, F2, F3, ... F8.
5. Nothing in this SOP changes any HTTP contract, response shape, or route path. If your edit
   would change one, you have misread the step — stop and re-read.

---

## F1 — Fix the missing `IntegrityError` import in `routers/media.py` (real bug)

**Problem:** `routers/media.py` catches `except IntegrityError:` (around line 153) but never
imports `IntegrityError`. Under a real concurrent duplicate-media-upload race this raises
`NameError` instead of gracefully deduping, and turns what should be a 200 into a 500 (plus
deletes the just-written storage object via the outer `except Exception:` handler).

**File:** `backend/routers/media.py`

**Current (top of file, lines 1–9):**
```python
from __future__ import annotations
import hashlib
import re
from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
```

**Replace with:**
```python
from __future__ import annotations
import hashlib
import re
from pathlib import Path
import uuid
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
```

That is the ONLY change: one new import line (`from sqlalchemy.exc import IntegrityError`)
inserted between the existing `from sqlalchemy import select` line and the
`from sqlalchemy.ext.asyncio import AsyncSession` line. Do not touch anything else in the file.

**Gate:** run the standard gate (see Ground rules #3). Also run, from `backend/`:
```
python -c "import ast; ast.parse(open('routers/media.py', encoding='utf-8').read())"
```
should print nothing and exit 0.

**Commit:**
```
fix(backend): import IntegrityError in routers/media.py (F1)

upload_media's concurrent-duplicate-upload race handler referenced IntegrityError
without importing it — a NameError under real concurrency that turned a graceful
200-dedup into a 500 and deleted the just-written storage object. One import line.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F2 — Restore `@observability.timed_recompute` to `recompute_batch_credit` (metrics regression)

**Problem:** Before the refactor, `@observability.timed_recompute` decorated
`recompute_batch_credit` directly (confirmed via git history), so every call site — `create_batch`,
`ingest_lab_hcorg`, all evidence endpoints via `_recompute_if_batch_exists` — reported into the
`RECOMPUTE_DURATION` Prometheus histogram. During the refactor the decorator was dropped from
`credit_engine.py` and instead landed on `apply_lab_results` in `services/lab.py` — a thin wrapper
called from only 2 of the ~5 call sites. Net effect: most recompute latency is now invisible to
Prometheus. This step moves the decorator back to where it belongs and removes it from the
wrapper (avoids double-timing when `apply_lab_results` calls `recompute_batch_credit`, which
would now itself be timed).

### F2a — `backend/credit_engine.py`

Find the function signature:
```python
async def recompute_batch_credit(
```

Confirm there is currently NO `@observability.timed_recompute` line directly above it, and
confirm `observability` is not yet imported at the top of the file (check the import block).

**If `observability` is not imported**, add this import near the other top-level imports (put it
alongside similar module-level imports, e.g. near `from jsonsafe import ...` or wherever the
existing import block is — do not reorder unrelated imports):
```python
import observability
```

**Then**, immediately above the `async def recompute_batch_credit(` line, add:
```python
@observability.timed_recompute
async def recompute_batch_credit(
```

i.e. insert exactly one decorator line directly before the existing `async def
recompute_batch_credit(` line. Do not change the function body, signature, or anything else in
the file.

### F2b — `backend/services/lab.py`

**Current (top of file, lines 1–13):**
```python
import json
import observability
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models import Batch
from credit_engine import recompute_batch_credit

@observability.timed_recompute




async def apply_lab_results(
```

**Replace with:**
```python
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models import Batch
from credit_engine import recompute_batch_credit

async def apply_lab_results(
```

This removes the `import observability` line, the `@observability.timed_recompute` decorator
line, and the 3 blank lines that followed it. `apply_lab_results` calls `recompute_batch_credit`
internally, which is now timed at the source (F2a) — timing it again here would double-count.
Do not touch anything else in the file (the function body below `async def apply_lab_results(...)`
is unchanged).

**Verify no other call site of `recompute_batch_credit` also carries a stray
`@observability.timed_recompute`** — run from `backend/`:
```
grep -rn "timed_recompute" --include=*.py .
```
Expected output: exactly ONE match, in `credit_engine.py`, directly above
`async def recompute_batch_credit(`. If you see any other match, STOP and report it — do not
remove it yourself.

**Gate:** standard gate (Ground rules #3). Additionally, from `backend/`:
```
python -c "import server; from server import app; print('ok')"
```
should print `ok` (confirms no import cycle / NameError was introduced by the new
`import observability` in credit_engine.py).

**Commit:**
```
fix(backend): restore recompute-latency metrics to recompute_batch_credit (F2)

@observability.timed_recompute had drifted from recompute_batch_credit (credit_engine.py)
onto apply_lab_results (services/lab.py) during the R5/R6 extraction, silently blinding
RECOMPUTE_DURATION for create_batch, ingest_lab_hcorg, and all evidence-triggered
recomputes. Moved back to the source function; removed from the wrapper to avoid
double-timing.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F3 — Remove dead imports in `routers/batches.py` (hygiene, zero behavior change)

**Problem:** `routers/batches.py` imports `json`, `uuid`, `timezone` (from `datetime`), `Request`
(from fastapi), and `observability` — none of which are used anywhere in the file. It also
imports `Response` twice in the same line. Verify each before removing — do not remove anything
still in use.

**File:** `backend/routers/batches.py`

**Step 1:** From `backend/`, run:
```
grep -n "json\.\|uuid\.\|timezone\|Request\b\|observability\." routers/batches.py
```
Confirm the ONLY matches are inside the import lines themselves (i.e., no actual usage in the
function bodies). If any of these names ARE used somewhere in the file body, do NOT remove that
one — only remove imports confirmed unused.

**Current (lines 1–19), assuming the grep above confirms all five are unused:**
```python
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Request, Response, Depends, Header, HTTPException, Response, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch, MediaFile
from geo import haversine_km, _evaluate_anchor
from schemas import BatchPayload, BatchResponse
from security import verify_signature
from credit_engine import recompute_batch_credit
from storage import get_storage
import observability
from settings import log
from jsonsafe import _as_utc
```

**Replace with:**
```python
from __future__ import annotations
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Response, Depends, Header, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from db import get_session
from models import Batch, MediaFile
from geo import haversine_km, _evaluate_anchor
from schemas import BatchPayload, BatchResponse
from security import verify_signature
from credit_engine import recompute_batch_credit
from storage import get_storage
from settings import log
from jsonsafe import _as_utc
```

Changes: dropped `import json`, `import uuid`, `timezone` (kept `datetime`), `Request` and the
duplicate `Response` from the fastapi import line, and `import observability`. `datetime` is
kept because `_as_utc`/timestamp comparisons still reference it — verify with:
```
grep -n "datetime\." routers/batches.py
```
If that grep shows zero matches in the function bodies too, then also drop `from datetime import
datetime` entirely (replace the line with nothing) — but only if genuinely unused; check first.

**Gate:** standard gate (Ground rules #3).

**Commit:**
```
chore(backend): drop dead imports in routers/batches.py (F3)

json, uuid, timezone, Request, and a duplicate Response import were carried over from
the R8 extraction but are unused in this file. No behavior change.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F4 — Centralize the 7 evidence schemas into `schemas.py`

**Problem:** R4/R8 intended ALL Pydantic request/response models to live in `schemas.py`. The 7
evidence payload classes (`TelemetryPayload`, `YieldPayload`, `MetadataPayload`,
`ApplicationPayload`, `MoisturePayload`, `CompositeSamplePayload`, `TransportEventPayload`) ended
up defined directly inside `routers/evidence.py` instead. This step moves them, with zero field
changes — pure relocation, same as R4 was for the original schema extraction.

**Step 1:** Open `backend/routers/evidence.py`. Locate the block of 7 `class ...Payload(BaseModel):`
definitions near the top of the file, below the imports. Copy that block EXACTLY as-is (every
field, every validator, every docstring/comment inside it) — do not paraphrase or "improve"
anything.

**Step 2:** Open `backend/schemas.py`. Append the copied block to the END of the file, unchanged.
If `schemas.py` doesn't already import `BaseModel`/`Field`/whatever the evidence classes need
(check the copied block's usages against `schemas.py`'s existing import line, e.g. `from pydantic
import BaseModel, Field`), extend that existing import line to include whatever's missing — do
not add a second, separate pydantic import line.

**Step 3:** Back in `backend/routers/evidence.py`, delete the 7 class definitions you just copied
(the whole block, nothing more). Add an import for them instead, placed alongside the file's
existing `from schemas import ...` import if one exists, or as a new import line near the top:
```python
from schemas import (
    ApplicationPayload,
    CompositeSamplePayload,
    MetadataPayload,
    MoisturePayload,
    TelemetryPayload,
    TransportEventPayload,
    YieldPayload,
)
```
(Alphabetical order, matching the convention used in `server.py`'s facade re-export blocks.)

**Step 4:** Open `backend/server.py`. In the `# ---- R4: schemas ----` re-export block, add the
same 7 names into the existing `from schemas import (...)` list, keeping the list alphabetically
sorted as it already is. Do NOT create a new import block — extend the existing R4 one.

**Step 5:** grep for any other place in the codebase that might import these 7 classes directly
from `routers.evidence` (unlikely, but check):
```
cd backend
grep -rn "from routers.evidence import\|routers\.evidence\." --include=*.py .
```
If anything imports one of the 7 classes from `routers.evidence`, update that import to pull from
`schemas` instead. If nothing matches, no further action needed.

**Gate:** standard gate (Ground rules #3), plus:
```
python -c "import server; from server import app; print('ok')"
```

**Commit:**
```
refactor(backend): move evidence Pydantic schemas into schemas.py (F4)

The 7 evidence payload classes (Telemetry/Yield/Metadata/Application/Moisture/
CompositeSample/TransportEvent) lived inline in routers/evidence.py instead of the
single canonical schemas.py, as R4/R8 originally intended. Pure relocation, no field
or behavior changes; server.py's facade re-export extended to match.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F5 — Delete the committed one-off migration scripts from `backend/`

**Problem:** `backend/clean_r9.py` and `backend/patch_server.py` are one-off, mechanical
text-surgery scripts that were used during the R8/R9 extraction to hack `server.py` apart
programmatically. They are not application code and were accidentally committed into the shipped
`backend/` package (part of commit `521a33c`).

**Step 1:** Confirm neither file is imported or referenced anywhere else in the codebase:
```
cd backend
grep -rn "clean_r9\|patch_server" --include=*.py .
```
Expected: no matches other than the files' own filenames (they should not appear in any `import`
statement, any test, or any doc other than this SOP / the audit report).

**Step 2:** Delete both files:
```
git rm backend/clean_r9.py backend/patch_server.py
```

**Gate:** standard gate (Ground rules #3).

**Commit:**
```
chore(backend): remove one-off migration scripts clean_r9.py / patch_server.py (F5)

Both were scratch text-surgery tools used once during the R8/R9 extraction and were
accidentally committed into the shipped backend/ package. Not application code; not
imported anywhere.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F6 — Delete the stray untracked `extract_r8.py` at the project root

**Problem:** `extract_r8.py` sits at the repo root (outside `backend/`), untracked by git,
leftover automation from the R8 extraction attempt.

**Step 1:** From the repo root, confirm it's untracked and unreferenced:
```
git status --short -- extract_r8.py
grep -rn "extract_r8" --include=*.py --include=*.md . 2>/dev/null
```
Expected: `git status` shows it as `??` (untracked); the grep should show no references from any
other file (its own filename in this SOP doesn't count).

**Step 2:** Delete it:
```
rm extract_r8.py
```

This file was never tracked, so there is nothing to `git rm` — just delete it from disk. It will
not show up in `git status` as a removal since it was never added.

**Gate:** standard gate (Ground rules #3). Also confirm `git status --short` no longer lists
`extract_r8.py`.

**Commit:** none needed (untracked file deletion leaves no diff to commit). Just note it in the
tracker as done.

---

## F7 — Fix `server.py`'s stale docstring ("R1–R9" → "R1–R10")

**File:** `backend/server.py`, line 5.

**Current:**
```python
the domain modules extracted during the P4.8 server.py refactor (R1–R9).
```

**Replace with:**
```python
the domain modules extracted during the P4.8 server.py refactor (R1–R10).
```

That is the only change in the file.

**Gate:** standard gate (Ground rules #3).

**Commit:**
```
docs(backend): fix stale "R1–R9" docstring in server.py facade (F7)

R10 (this file's own shrink-to-facade step) was missing from its own docstring.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## F8 — Point `test_no_enforced_false_bypass_in_server_source` at the real source of truth

**Problem:** This regression test greps `server.py`'s source text for the literal string
`"enforced=False"`. Before the refactor, the attestation-enforcement logic actually lived in
`server.py`, so this was a meaningful guard. Now that logic lives in `settings.py`
(`_attestation_enforced`), and `server.py` is a 139-line facade of imports — the test still
passes, but it is no longer scanning the module that contains the logic it claims to guard. This
step widens the test to scan the real source files, without weakening it.

**File:** `backend/tests/test_annual_gates_t13_t14.py`

**Current (around line 174–182):**
```python
def test_no_enforced_false_bypass_in_server_source():
    """Regression: the hardcoded PAH bypass must never come back."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "server.py").read_text(
        encoding="utf-8"
    )
    assert "enforced=False" not in src
```

**Replace with:**
```python
def test_no_enforced_false_bypass_in_server_source():
    """Regression: the hardcoded PAH bypass must never come back.

    Post-refactor (R1-R10), server.py is a facade; the actual attestation/compliance
    logic this guards lives in settings.py and services/compliance.py. Scan those
    (and server.py, for good measure) rather than just the facade.
    """
    from pathlib import Path

    backend_dir = Path(__file__).resolve().parents[1]
    for filename in ("server.py", "settings.py", "services/compliance.py"):
        src = (backend_dir / filename).read_text(encoding="utf-8")
        assert "enforced=False" not in src, f"found in {filename}"
```

Do not change the test's name, its position in the file, or anything else nearby.

**Gate:** standard gate (Ground rules #3). Specifically confirm this one test still passes:
```
cd backend
DMRV_DISABLE_DOTENV=1 python -m pytest -q tests/test_annual_gates_t13_t14.py::test_no_enforced_false_bypass_in_server_source
```

**Commit:**
```
test(backend): widen enforced=False regression scan to settings.py/services (F8)

The attestation-enforcement logic this test guards moved to settings.py during the
refactor; the test was still only scanning the now-mostly-empty server.py facade.

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
```

---

## Final wrap-up (after F1–F8 all committed)

1. Run the full gate one more time from `backend/`:
   ```
   DMRV_DISABLE_DOTENV=1 python -m pytest -q --tb=short -rf
   ```
   Expect **416 passed, 2 skipped** (same count as before F1–F8 — none of these fixes add or
   remove tests except F8, which only edits an existing test's body).
2. Run the portal gate from `portal/`:
   ```
   npm run typecheck && npx vitest run && npx vite build
   ```
   Expect: typecheck clean, **19 passed**, build OK.
3. Report a short summary: which of F1–F8 were completed, final test counts, nothing else
   changed. STOP.
