"""Create (or update) a portal user — server-side bootstrap, not an endpoint.

An HTTP "create first admin" route is a standing backdoor; instead an operator
with DB access runs this script once. Usage (from backend/, with DATABASE_URL
set):

    python create_portal_user.py --email admin@example.org --role admin
    # password read from the DMRV_PORTAL_PASSWORD env var, or prompted if a TTY

Re-running for an existing email updates that user's password/role (idempotent
rotation), never creating a duplicate.
"""

import argparse
import asyncio
import os
import sys

from sqlalchemy import select

from db import SessionLocal
from models import PortalUser
from portal.auth import VALID_ROLES, hash_password


async def _upsert(email: str, password: str, role: str) -> str:
    async with SessionLocal() as session:
        existing = (
            await session.execute(
                select(PortalUser).where(PortalUser.email == email)
            )
        ).scalar_one_or_none()
        if existing is not None:
            existing.password_hash = hash_password(password)
            existing.role = role
            existing.disabled = False
            action = "updated"
        else:
            session.add(
                PortalUser(
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    disabled=False,
                )
            )
            action = "created"
        await session.commit()
        return action


def main() -> int:
    parser = argparse.ArgumentParser(description="Create/update a portal user.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=VALID_ROLES)
    args = parser.parse_args()

    password = os.environ.get("DMRV_PORTAL_PASSWORD")
    if not password and sys.stdin.isatty():
        import getpass

        password = getpass.getpass("Portal user password: ")
    if not password:
        print(
            "Password required: set DMRV_PORTAL_PASSWORD or run interactively.",
            file=sys.stderr,
        )
        return 2

    action = asyncio.run(_upsert(args.email, password, args.role))
    print(f"portal user {action}: {args.email} ({args.role})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
