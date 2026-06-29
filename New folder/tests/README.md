# Hardening test suite

This directory contains test files that map 1-to-1 to the issues in
`/app/detailed.md`. Each test name encodes the issue id (`p0_12`, `p1_17`,
etc.) so you can run a single fix's verification with:

```bash
# Backend (Python)
python -m pytest /app/tests/backend/test_hardening.py -k p0_13 -q

# Frontend (Dart)
flutter test /app/tests/dart/pyrolysis_writer_retake_test.dart
```

## Layout

```
/app/tests/
├── README.md                    ← you are here
├── backend/
│   ├── conftest.py              ← shared fixtures (engine, client)
│   └── test_hardening.py        ← P0-12..P1-21 verification (Python)
└── dart/
    ├── pyrolysis_writer_retake_test.dart           # P0-19
    ├── location_service_release_guard_test.dart    # P0-20
    ├── sign_inside_transaction_test.dart           # P1-16
    ├── migration_v11_normalise_timestamp_test.dart # P1-17
    ├── no_backup_manifest_test.dart                # P1-22
    ├── pyrolysis_json_check_test.dart              # P1-23
    └── database_provider_autodispose_test.dart     # P2-1
```

## Running the Python suite

The Python tests target the FastAPI app inside the uploaded zip at
`/app/uploaded/New folder/backend/`. The `conftest.py` adds this directory
to `sys.path` automatically.

```bash
pip install pytest pytest-asyncio httpx aiosqlite
python -m pytest /app/tests/backend/ -q
```

### Expected state before fixes are applied

Many tests will **FAIL** against the un-fixed codebase. This is intentional:
the suite is the *contract* for what a correct fix looks like. Per-issue
expected pre-fix outcomes:

| Issue  | Pre-fix outcome                                         |
|--------|---------------------------------------------------------|
| P0-12  | Extra-field test FAILS (server uses extra="ignore")     |
| P0-13  | Different-payload-same-op-id returns 200 (wrong)        |
| P0-14  | `PyrolysisTelemetry` model not defined → AttributeError |
| P0-15  | Stub endpoints accept any dict → 201 (wrong)            |
| P0-16  | min_temp=50 currently accepted (wrong)                  |
| P0-17  | Hardcoded default still in db.py                        |
| P0-18  | `backend/alembic/` does not exist                       |
| P1-18  | No X-Mock-Location header check                         |
| P1-19  | HMAC verifies body-only; cross-endpoint replay accepted |
| P1-20  | `..` in filename leaks into stored path                 |
| P1-21  | `schemas.py` still uses `@field_validator`              |

### After fixes are applied

```bash
python -m pytest /app/tests/backend/ -q
# Expected: ====== N passed, 0 failed ======
```

## Running the Dart suite

Templates live in `/app/tests/dart/`. They are designed to be **copied**
into the project's `test/` directory so Flutter's package resolver can
find `package:dmrv_app/...` imports.

```bash
cp /app/tests/dart/*.dart "/app/uploaded/New folder/test/"
cd "/app/uploaded/New folder"
flutter pub get
flutter test test/
```

Where a template depends on infrastructure that does not yet exist (e.g.
a Drift schema-history fixture for migration v11), it calls
`markTestSkipped()` with a clear TODO message rather than failing
silently.

## "Dumb agent" mode

Every assertion in this suite is keyed to a section of
`/app/detailed.md`. If a test fails, the `reason:` string tells you which
issue and where to read about it. Do not edit the tests to make them
pass. Edit the source per the spec until the test passes.
