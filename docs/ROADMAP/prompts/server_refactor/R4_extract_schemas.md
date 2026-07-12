# R4 — Extract `schemas.py` (all Pydantic request/response models)

> **Read `00_SERVER_REFACTOR_SOP.md` first.** Step 4 of 10. R1–R3 must be committed & green. Pure relocation.
> Baseline gate: **416 passed, 2 skipped**. ONE commit. Do not start R5.

**What moves:** every Pydantic `BaseModel` class in server.py. This is the largest batch of symbols
(~350 LOC) but they are structurally trivial — data-only classes with no app/db/session dependencies.

**The models to move (in server.py order):**
1. `BatchPayload` (~line 508, depends on `CORG_TABLE` from `lca_engine`)
2. `BatchResponse` (~line 595)
3. `MediaUploadResponse` (~line 607)
4. `RegistrationRequest` (~line 613)
5. `RegistrationResponse` (~line 618)
6. `MintTokenRequest` (~line 853)
7. `LabHCorgRequest` (~line 886)
8. `LabResultsRequest` (~line 894)
9. `_BatchScopedPayload` (~line 2172, base class for evidence payloads)
10. `TelemetryPayload` (~line 2193)
11. `YieldPayload` (~line 2224)
12. `MetadataPayload` (~line 2237)
13. `ApplicationPayload` (~line 2247)
14. `MoisturePayload` (~line 2267)
15. `CompositeSamplePayload` (~line 2278)
16. `TransportEventPayload` (~line 2292)
17. `KilnRequest` (~line 2521)
18. `OperatorTrainingRequest` (~line 2530)
19. `SupervisorVisitRequest` (~line 2539)
20. `ScaleCalibrationRequest` (~line 2548)
21. `AnnualVerificationRequest` (~line 2608)

**Dependencies:**
- `BaseModel`, `ConfigDict`, `Field`, `field_validator` from `pydantic`
- `UUID` from `uuid`
- `Optional`, `Literal` from `typing`
- `datetime` from `datetime`
- `CORG_TABLE` from `lca_engine` (used by `BatchPayload.validate_feedstock`)
- `uuid` module (used by `_BatchScopedPayload._canonicalize_batch_uuid`)

---

## STEP 1 — Create `backend/schemas.py`

Create `backend/schemas.py`. Copy ALL 21 model classes verbatim from server.py, preserving their exact
field definitions, validators, docstrings, and comments.

```python
"""Pydantic request/response models (extracted from server.py, R4).

Strict V2 models with ConfigDict(extra="forbid") and range-checked fields.
No app/db/session dependencies — these are pure data schemas.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from lca_engine import CORG_TABLE


# ==================== Batch payload + response ====================


class BatchPayload(BaseModel):
    # ... copy the ENTIRE class verbatim from server.py lines ~508–592 ...
    pass  # PLACEHOLDER — replace with the real verbatim copy


class BatchResponse(BaseModel):
    # ... copy verbatim from server.py lines ~595–604 ...
    pass


class MediaUploadResponse(BaseModel):
    # ... copy verbatim from server.py lines ~607–610 ...
    pass


class RegistrationRequest(BaseModel):
    # ... copy verbatim from server.py lines ~613–615 ...
    pass


class RegistrationResponse(BaseModel):
    # ... copy verbatim from server.py lines ~618–620 ...
    pass


class MintTokenRequest(BaseModel):
    # ... copy verbatim from server.py lines ~853–855 ...
    pass


# ==================== Lab models ====================


class LabHCorgRequest(BaseModel):
    # ... copy verbatim from server.py lines ~886–891 ...
    pass


class LabResultsRequest(BaseModel):
    # ... copy verbatim from server.py lines ~894–925 ...
    pass


# ==================== Evidence-endpoint schemas (Phase 11) ====================


class _BatchScopedPayload(BaseModel):
    # ... copy verbatim from server.py lines ~2172–2190 ...
    pass


class TelemetryPayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2193–2221 ...
    pass


class YieldPayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2224–2234 ...
    pass


class MetadataPayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2237–2244 ...
    pass


class ApplicationPayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2247–2264 ...
    pass


class MoisturePayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2267–2275 ...
    pass


class CompositeSamplePayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2278–2289 ...
    pass


class TransportEventPayload(_BatchScopedPayload):
    # ... copy verbatim from server.py lines ~2292–2303 ...
    pass


# ==================== Admin registry models (C8/C9) ====================


class KilnRequest(BaseModel):
    # ... copy verbatim from server.py lines ~2521–2527 ...
    pass


class OperatorTrainingRequest(BaseModel):
    # ... copy verbatim from server.py lines ~2530–2536 ...
    pass


class SupervisorVisitRequest(BaseModel):
    # ... copy verbatim from server.py lines ~2539–2545 ...
    pass


class ScaleCalibrationRequest(BaseModel):
    # ... copy verbatim from server.py lines ~2548–2554 ...
    pass


class AnnualVerificationRequest(BaseModel):
    # ... copy verbatim from server.py lines ~2608–2622 ...
    pass
```

> **CRITICAL:** The `pass` placeholders above are NOT the real content. You MUST read each class body from
> `server.py` by its line numbers and copy it **byte-for-byte** into `schemas.py`. The line numbers are hints;
> find each class by name. Include all `field_validator` methods, all docstrings, all comments.

---

## STEP 2 — Edit `backend/server.py`

1. **Delete** all 21 model class definitions from server.py. They are in two blocks:
   - The main batch/response/registration models (~lines 508–620)
   - `MintTokenRequest` (~line 853–855)
   - `LabHCorgRequest`, `LabResultsRequest` (~lines 886–925)
   - `_BatchScopedPayload` + 7 evidence payloads (~lines 2172–2303)
   - 5 admin request models (~lines 2521–2554, 2608–2622)
   - Also delete the section comment lines (`# ==================== Pydantic Models ====================` etc.)
     but ONLY the ones that directly precede the deleted classes.

2. **Add re-export import** in server.py's local-import block (after the R3 imports):
   ```python
   from schemas import (  # noqa: F401  (R4 facade)
       AnnualVerificationRequest,
       ApplicationPayload,
       BatchPayload,
       BatchResponse,
       CompositeSamplePayload,
       KilnRequest,
       LabHCorgRequest,
       LabResultsRequest,
       MediaUploadResponse,
       MetadataPayload,
       MintTokenRequest,
       MoisturePayload,
       OperatorTrainingRequest,
       RegistrationRequest,
       RegistrationResponse,
       ScaleCalibrationRequest,
       SupervisorVisitRequest,
       TelemetryPayload,
       TransportEventPayload,
       YieldPayload,
       _BatchScopedPayload,
   )
   ```

3. **Check now-dead imports:** After the delete, server.py may no longer directly use `field_validator`,
   `ConfigDict`, or `Literal` from pydantic/typing. **Only remove if grep confirms zero remaining uses.**
   `BaseModel` is likely still referenced (keep it). `UUID` from `uuid` is used in route handlers (keep it).

---

## STEP 3 — Gates (from `backend/`)

1. **G3:** `DMRV_DISABLE_DOTENV=1 python -c "import server; from server import BatchPayload, TelemetryPayload, AnnualVerificationRequest, _BatchScopedPayload; print('ok')"` → `ok`.
2. **G1:** `DMRV_DISABLE_DOTENV=1 python -m pytest -q` → **416 passed, 2 skipped**.
   - Watch: every test that constructs a payload or references a schema class — these are the most
     widely-imported symbols, so a missing re-export will show fast.

---

## STEP 4 — Commit + tick

- Tracker: `- [x] **P4.8/R4** — extracted schemas.py (all Pydantic models); server.py ~2330→~1980; 416/2 green`
- Commit:
  ```
  refactor(backend): extract schemas.py Pydantic models — server.py ~2330→~1980 LOC (P4.8/R4)

  Pure relocation, no behavior change. 21 request/response models moved.
  Suite green (416 passed, 2 skipped). Facade re-exports preserve import surface.

  Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>
  ```

Report 3-liner, then STOP.
