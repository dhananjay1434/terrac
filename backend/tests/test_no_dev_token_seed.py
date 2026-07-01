"""Phase R2 — the dev-token enrollment backdoor is gone and cannot be reseeded.

Phase 3 removed the special-case from register_device, but db.py init_db() still
unconditionally seeded a well-known enrollment token and reset its used_at on
every boot — a permanent production backdoor. This locks in its removal:
  1. source-guard: the literal token string no longer appears in db.py;
  2. behavior: no such token exists in a fresh DB, and registering with it is
     rejected as an invalid enrollment token.
"""

import json
from pathlib import Path

import pytest
from sqlalchemy.future import select

from models import EnrollmentToken

_DEV_TOKEN = "dev-token"


def test_db_source_has_no_dev_token_seed():
    db_src = (Path(__file__).resolve().parents[1] / "db.py").read_text(encoding="utf-8")
    assert _DEV_TOKEN not in db_src, "db.py still references the dev-token seed"


@pytest.mark.asyncio
async def test_fresh_db_has_no_dev_token(session_factory):
    async with session_factory() as s:
        row = (
            await s.execute(
                select(EnrollmentToken).where(EnrollmentToken.token == _DEV_TOKEN)
            )
        ).scalar_one_or_none()
    assert row is None, "a dev-token enrollment row was seeded into a fresh DB"


@pytest.mark.asyncio
async def test_register_with_dev_token_is_rejected(client):
    from tests.remediation.crypto_utils import TEST_PUBLIC_KEY_B64

    r = await client.post(
        "/api/v1/register",
        content=json.dumps(
            {"device_id": "dev-attacker", "public_key": TEST_PUBLIC_KEY_B64}
        ).encode("utf-8"),
        headers={"X-Enrollment-Token": _DEV_TOKEN},
    )
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "invalid_enrollment_token"
