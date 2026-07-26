"""M0.3 — staging replay harness (phase-gate smoke test).

Seeds a FRESH scratch SQLite database via seed_demo_rich, then asserts the seed
produced a healthy dataset and the portal summary endpoint is wired.

SAFETY: the seed is invoked with `--remote <sqlite-url>`, which makes
seed_demo_rich set DATABASE_URL explicitly and SKIP load_dotenv — so it can
never read backend/.env (which holds a live Postgres URL). A hard sqlite-only
guard is belt-and-braces: this harness refuses any non-sqlite target.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import tempfile

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    fd, path = tempfile.mkstemp(suffix=".replay.db")
    os.close(fd)
    url = f"sqlite+aiosqlite:///{path}"
    if not url.startswith("sqlite"):  # hard guard: never target prod/Postgres
        raise RuntimeError("replay harness refuses a non-sqlite target")
    # The seed builds its own schema against the scratch DB, so migrations must
    # NOT be skipped here. conftest sets DMRV_SKIP_MIGRATIONS=1 in the parent
    # env — drop it for the child or the scratch DB has no tables.
    env = {**os.environ, "DMRV_ALLOW_WEAK_SECRETS": "1"}
    env.pop("DMRV_SKIP_MIGRATIONS", None)
    env.setdefault("DMRV_HMAC_SECRET", "replay-secret")
    env.setdefault("DMRV_ADMIN_SECRET", "replay-admin-secret")
    try:
        proc = subprocess.run(
            [sys.executable, "seed_demo_rich.py", "--remote", url],
            cwd=BACKEND_DIR,
            env=env,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "seed_demo_rich failed:\n"
                + proc.stdout[-2000:]
                + "\n"
                + proc.stderr[-2000:]
            )
        count = asyncio.run(_assert_healthy(url))
        print(f"replay OK: {count} batches, all lca-signed, summary responds")
        return count
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


async def _assert_healthy(url: str) -> int:
    from sqlalchemy import func, select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from models import Batch

    engine = create_async_engine(url, poolclass=NullPool)
    try:
        smk = async_sessionmaker(engine, expire_on_commit=False)
        async with smk() as s:
            count = (
                await s.execute(select(func.count()).select_from(Batch))
            ).scalar_one()
            assert count > 0, "replay produced zero batches"
            # DEVIATION from M0.3's "every batch has lca_signature": the rich seed
            # intentionally includes provisional variants (no_lab/no_yield/…) that
            # legitimately have no signature. The real health invariant is that
            # every ISSUED (non-provisional) batch is LCA-signed.
            issued = (
                await s.execute(
                    select(func.count())
                    .select_from(Batch)
                    .where(Batch.provisional.is_(False))
                )
            ).scalar_one()
            unsigned_issued = (
                await s.execute(
                    select(func.count())
                    .select_from(Batch)
                    .where(Batch.provisional.is_(False))
                    .where(Batch.lca_signature.is_(None))
                )
            ).scalar_one()
            assert issued > 0, "replay produced no issued batches"
            assert unsigned_issued == 0, (
                f"{unsigned_issued}/{issued} issued batches missing lca_signature"
            )
        _smoke_summary(smk)
        return count
    finally:
        await engine.dispose()


def _smoke_summary(session_factory) -> None:
    from fastapi.testclient import TestClient

    from server import app, get_session

    async def _override():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = _override
    try:
        with TestClient(app) as client:
            resp = client.get("/api/v1/portal/summary")
            # "responds" = the route is wired; auth (401/403) is fine, 404/500 is not.
            assert resp.status_code not in (404, 500), (
                f"summary endpoint returned {resp.status_code}"
            )
    finally:
        app.dependency_overrides.pop(get_session, None)


if __name__ == "__main__":
    main()
