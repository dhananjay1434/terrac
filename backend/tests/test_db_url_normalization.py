"""Deploy hardening: DATABASE_URL from managed Postgres providers (Render,
Heroku, Supabase) arrives with no async driver. normalize_db_url must upgrade it
to +asyncpg so the async engine and the startup Alembic migration both boot.
"""

from db import normalize_db_url


def test_bare_postgresql_gets_asyncpg():
    assert (
        normalize_db_url("postgresql://u:p@host:5432/db")
        == "postgresql+asyncpg://u:p@host:5432/db"
    )


def test_legacy_postgres_scheme_gets_asyncpg():
    # Heroku-style postgres:// (SQLAlchemy 2.0 rejects this scheme outright).
    assert (
        normalize_db_url("postgres://u:p@host/db")
        == "postgresql+asyncpg://u:p@host/db"
    )


def test_already_asyncpg_is_unchanged():
    url = "postgresql+asyncpg://u:p@host/db"
    assert normalize_db_url(url) == url


def test_explicit_sync_driver_is_left_alone():
    # An operator who explicitly pins psycopg2 keeps it.
    url = "postgresql+psycopg2://u:p@host/db"
    assert normalize_db_url(url) == url


def test_sqlite_is_untouched():
    url = "sqlite+aiosqlite:///:memory:"
    assert normalize_db_url(url) == url
