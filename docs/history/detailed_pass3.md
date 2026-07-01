# TerraCipher / Kon-Tiki dMRV — Third-pass findings (NEW, not in either audit)

> Source files re-read for this pass:
> `backend/server.py` (whole file), `backend/lca_engine.py`,
> `lib/services/crypto_signer.dart`, `lib/data/local/passphrase_resolver.dart`,
> `lib/data/local/app_database.dart`.
>
> Each issue below is genuinely new — cross-checked against both
> "additional findings (P0-12 → P2-2)" and the "hand-holding prompt
> (P0-1 → P0-11)" documents. None of them duplicate.

---

## P0-21 — `DMRV_HMAC_SECRET` defaults to the literal string `"default_secret"`

**File:** `backend/server.py:124`

```python
secret = os.environ.get("DMRV_HMAC_SECRET", "default_secret").encode("utf-8")
```

This is the **same class of bug** as P0-17 (hardcoded DB default) but for the
HMAC secret. A staging or test container that forgets to set
`DMRV_HMAC_SECRET` accepts every request signed with the well-known string
`"default_secret"`. Worse, the variable name is suggestive — anyone who
greps the source knows the fallback. The audit's P0-2 (per-device keys)
fixes this **structurally**, but until P0-2 lands, every deploy where the
env var is missing accepts forged HMACs.

**Fix:** mirror P0-17 — fail fast on missing env:
```python
_HMAC_SECRET = os.environ.get("DMRV_HMAC_SECRET")
if not _HMAC_SECRET:
    raise RuntimeError("DMRV_HMAC_SECRET env var is required.")
secret = _HMAC_SECRET.encode("utf-8")
```
Move it to module scope so the error is raised at startup, not on first
request.

**Severity:** P0 — a single misconfigured environment grants forge-anything
access to anyone who reads the GitHub source.

---

## P0-22 — IntegrityError race in `create_batch` accepts ANY second-writer's payload as a duplicate

**File:** `backend/server.py:207–221`

```python
except IntegrityError:
    await session.rollback()
    stmt = select(Batch).where(Batch.batch_uuid == payload.batch_uuid)
    result = await session.execute(stmt)
    batch = result.scalar_one()
    log.info(f"[batches] RACE-RESOLVED batch_uuid={payload.batch_uuid}")
    return BatchResponse(
        batch_uuid=str(batch.batch_uuid),
        ...
        duplicate=True,
        ...
    )
```

If two concurrent requests share a `batch_uuid` but carry **different**
`sha256_hash`, moisture, or yield, the second arrival hits
`IntegrityError` on the `unique(batch_uuid)` constraint, the handler
re-reads the **winning** row, and returns 201/200 with `duplicate=True` —
without ever telling the loser that its payload was discarded. The client
treats this as success and deletes the local evidence. The other half of
the data — the loser's photo, GPS, and moisture — is gone forever.

This is the **race-condition sibling** of P0-13 (duplicate idempotency
key with different payload). Both must be fixed identically.

**Fix:** in the `except IntegrityError:` branch, compare hashes before
returning 200:
```python
if (batch.sha256_hash.lower() != payload.sha256_hash.lower()
    or batch.operation_id != x_idempotency_key):
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="race_resolved_with_different_payload",
    )
```

**Severity:** P0 — silent data loss under concurrent sync.

---

## P0-23 — `get_corg` is case-sensitive → silent under-issuance

**File:** `backend/lca_engine.py:84–86`, `CORG_TABLE` (line 23).

```python
def get_corg(feedstock_species: str) -> float:
    return CORG_TABLE.get(feedstock_species, CORG_TABLE["Default"])
```

`CORG_TABLE` keys are `"Lantana_camara"`, `"Wood_chips"`, etc. A client
that sends `"lantana_camara"` (lowercase) or `"Lantana Camara"` (space) or
trailing whitespace silently falls through to the `Default` of **0.55**
instead of Lantana's **0.60**. That is an 8.3 % under-credit per batch
for every producer whose client serialises species in the "wrong" case.

The Pydantic model has `str_strip_whitespace=True` *only inside `schemas.py`*
(now dead code per P0-12). The flat `BatchPayload` in `server.py` does
**not** strip whitespace.

**Fix:**
1. Normalise on lookup:
   ```python
   def get_corg(feedstock_species: str) -> float:
       key = (feedstock_species or "").strip()
       # Build a case-insensitive map ONCE at import time.
       return _CORG_LOOKUP_CI.get(key.casefold(), CORG_TABLE["Default"])
   ```
   Where:
   ```python
   _CORG_LOOKUP_CI = {k.casefold(): v for k, v in CORG_TABLE.items()}
   ```
2. **Better**: enforce strict matching at the validator (P0-12 already
   suggests adding `feedstock_species in CORG_TABLE`). Make the validator
   normalise *and* assert, so "lantana_camara" is **rejected** rather than
   silently downgraded.

**Severity:** P0 — under-issuance is a financial bug, just inverted.
A producer is owed credit they don't get; this is harder to detect than
over-issuance because nobody complains except the producer (who has no
visibility into the formula).

---

## P0-24 — No request size limit → upload OOM DoS

**File:** `backend/server.py:255–307` (`upload_media`).

FastAPI/Starlette does not enforce a default request-size cap. The
`upload_media` handler does:
```python
content = await file.read()
calculated_hash = hashlib.sha256(content).hexdigest()
```
A hostile client sending a 10 GB multipart body will pin a worker for
minutes and OOM the container. There is no `max_size`, no streaming
ingest, and the SHA-256 is computed in one shot.

**Fix:** at minimum, reject early:
```python
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB — well above any biochar photo
...
content = await file.read()
if len(content) > MAX_UPLOAD_BYTES:
    raise HTTPException(status_code=413, detail="file_too_large")
```
Better: stream the upload through `hashlib.sha256().update(chunk)` and abort
once `MAX_UPLOAD_BYTES` is exceeded. Even better: reverse proxy
(nginx / Caddy / Cloudflare) enforces it before FastAPI ever sees the bytes.

**Severity:** P0 — single hostile request takes the API down.

---

## P0-25 — `Batch.batch_uuid` is unique but `MediaFile` has no FK to `Batch`

**File:** `backend/models.py:43–55`.

`MediaFile` stores `operation_id` and `sha256_hash` but has **no
`batch_uuid` column at all**. The link from a photo to its parent batch
exists only client-side (in the Flutter row's `sha256_hash` field). The
server cannot answer "which photos belong to batch X" in a single join.

Consequences:
1. Garbage collection of orphan photos is impossible without a full table
   scan + heuristic match.
2. The proof-wallet UI's "photo anchored on server" promise is informal —
   nothing on the server side enforces that the photo whose SHA-256 the
   batch references actually exists in `media_files`. A batch can be
   `RECEIVED` with `sha256_hash = "deadbeef…"` and **no media row at all**.

**Fix:**
1. Add `batch_uuid` column to `MediaFile` with a FK to `batches.batch_uuid`.
2. In `create_batch`, after the batch row is committed, verify a
   `MediaFile` row exists with the same `sha256_hash`. If not, mark the
   batch `status="UNVERIFIED"` (consistent with current naming).
   Alternative: require photo upload BEFORE batch creation, and reject
   `create_batch` if the referenced `sha256_hash` is not yet anchored.

**Severity:** P0 — the entire proof-wallet integrity promise is currently
client-honour-based, server-unenforced.

---

## P1-24 — CORS: `allow_origins=["*"]` combined with `allow_credentials=True`

**File:** `backend/server.py:40–46`.

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Per CORS spec, `Access-Control-Allow-Origin: *` is **invalid** when
`Access-Control-Allow-Credentials: true`. Browsers will drop the
combination silently, so practical impact today is minor — but the
intent (cookies/Authorization across origins) is mis-encoded and will
break the day someone adds session auth. Also, `allow_methods=["*"]` and
`allow_headers=["*"]` are wider than needed.

**Fix:** enumerate the actual origins (mobile app uses no Origin header
at all; web admin should be a named list). Drop
`allow_credentials=True` unless you actually use cookies.

```python
CORS_ALLOW_ORIGINS = os.environ.get("CORS_ALLOW_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in CORS_ALLOW_ORIGINS if o],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Idempotency-Key", "X-HMAC-Signature",
                   "X-Declared-SHA256", "X-Device-Id", "X-Mock-Location"],
)
```

**Severity:** P1 — defence in depth; not exploitable today but trivially
exploitable tomorrow once session auth lands.

---

## P1-25 — `@app.on_event("startup")` is deprecated (Pydantic V2 / FastAPI 0.100+)

**File:** `backend/server.py:53–56`.

```python
@app.on_event("startup")
async def startup():
    await init_db()
```

FastAPI deprecated `on_event` in favour of the lifespan context-manager
API. The deprecation warning shows up in test output (we observed it in
the hardening test run). Won't crash today, **will** crash on the
FastAPI release that removes it.

**Fix:**
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    log.info("Database initialized")
    yield

app = FastAPI(
    title="Kon-Tiki dMRV API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
```

**Severity:** P1 — silent forward-compat trap.

---

## P1-26 — Logging declared SHA-256 leaks evidence-of-attempt for forgery analysis

**File:** `backend/server.py:298`.

```python
log.warning(f"[media] SHA256 MISMATCH declared={x_declared_sha256} calculated={calculated_hash}")
```

Logging the *declared* hash on mismatch is fine for debugging but also
hands an attacker (who can see logs, e.g. via aggregated log services
like Datadog with broad IAM) a confirmation oracle: every failed forge
attempt is recorded with the exact bytes the attacker wanted to convince
the server it had. Combined with retry logic this is a workable
exfiltration channel.

**Fix:** log only the first 8 hex chars of each side, and use structured
logging fields instead of f-string interpolation:
```python
log.warning("[media] SHA256 mismatch",
            extra={"declared_prefix": x_declared_sha256[:8],
                   "calculated_prefix": calculated_hash[:8],
                   "op_id": x_idempotency_key})
```

**Severity:** P1 — operational hygiene.

---

## P1-27 — `CryptoSigner._keyFuture` static cache is never refreshed when the underlying secure-storage key is rotated externally

**File:** `lib/services/crypto_signer.dart:15–30`.

```dart
static Future<List<int>>? _keyFuture;

static Future<List<int>> _resolveKey() {
  return _keyFuture ??= _readOrCreateOnce();
}
```

If a sibling code path (e.g. `secureWipe` in `app_database.dart:316`)
deletes the secure-storage entry and a different code path then asks
`CryptoSigner.signPayload(...)` **without** first calling
`CryptoSigner.clear()`, the static `_keyFuture` returns the OLD key bytes
from memory. The next write then signs with a key whose secure-storage
counterpart is gone — server verification will fail forever, all subsequent
outbox rows are unverifiable.

`secureWipe` does call `ctx.clearHmacKey()` (line 315), which presumably
calls `CryptoSigner.clear()`. But there's no static analyzer enforcing
that every `clearHmacKey()` implementation invalidates the cache — and the
audit's P0-10 (wipe-context interface) didn't pin this.

**Fix:** add an explicit invariant test:
```dart
test('clearHmacKey on WipeContext invalidates the static CryptoSigner cache', () async {
  await CryptoSigner.warmUp();
  // ... wipe via the production code path ...
  // ... then assert that CryptoSigner.signPayload yields a DIFFERENT signature
  //     for the same input bytes ...
});
```
And: make `CryptoSigner` instance-based and inject it via Riverpod, so
the static cache vanishes entirely. (Larger fix — defer to a follow-up.)

**Severity:** P1 — silent integrity break across a wipe.

---

## P1-28 — `passphrase_resolver` uses `Random.secure()` directly without seeding fallback for platforms where it's not available

**File:** `lib/data/local/passphrase_resolver.dart:33–35`.

```dart
final rng = Random.secure();
final bytes = List<int>.generate(32, (_) => rng.nextInt(256));
```

`Random.secure()` throws `UnsupportedError` on some restricted Flutter
targets (older Android emulators without `/dev/urandom` access, certain
embedded ChromeOS containers). If this throws inside the
`resolveOrCreatePassphrase` future, the AppDatabase singleton will never
resolve — the app is bricked.

**Fix:** catch the `UnsupportedError`, log, and refuse to start with a
clear UX message rather than a hang. This is a fail-loud requirement, not
a fall-back-to-`Random()` — falling back to non-secure RNG for the DB
encryption passphrase would be catastrophic.

```dart
late final Random rng;
try {
  rng = Random.secure();
} on UnsupportedError catch (e) {
  throw StateError(
    'Secure RNG not available on this platform. '
    'Refusing to generate a DB passphrase. ($e)',
  );
}
```

**Severity:** P1 — platform-dependent crash, not an injection.

---

## P2-3 — `Batch.harvest_uptime_seconds` is `nullable=True` server-side, but the audit P0-3 made it mandatory client-side

**File:** `backend/models.py:31`, `backend/server.py:71`.

```python
harvest_uptime_seconds: Mapped[int] = mapped_column(Integer, nullable=True)
```
and
```python
harvest_uptime_seconds: Optional[int] = Field(None, ge=0)
```

After the audit's clock-spoof defence (P0-3) lands, the client treats
`harvest_uptime_seconds` as mandatory. The server still accepts `None`.
A malicious client can simply omit the field and bypass the wall-clock
cross-check entirely.

**Fix:** make it required server-side once the client rollout is
confirmed:
```python
harvest_uptime_seconds: int = Field(..., ge=0)
```
And `nullable=False` on the ORM column (backfill existing rows with `0`
or migrate; new column on table-rewrite).

**Severity:** P2 — only matters once P0-3 has shipped client-side AND
the audit's wall-clock cross-check is wired in server-side. Track as a
follow-up gated on those.

---

## P2-4 — `lca_engine.CORG_TABLE` is a mutable module-level dict

**File:** `backend/lca_engine.py:23–28`.

```python
CORG_TABLE: Dict[str, float] = {
    "Lantana_camara": 0.60,
    ...
}
```

Any test or import-time helper that mutates this dict (e.g.
`CORG_TABLE["Test_species"] = 0.99`) persists across the entire test
process. There is no `freeze` or `MappingProxyType` wrapper. A subtle
test-ordering bug can silently change credit-issuance constants for
later tests.

**Fix:** expose a read-only proxy:
```python
from types import MappingProxyType
_CORG_RAW = {"Lantana_camara": 0.60, ...}
CORG_TABLE: Mapping[str, float] = MappingProxyType(_CORG_RAW)
```

**Severity:** P2 — defence-in-depth.
