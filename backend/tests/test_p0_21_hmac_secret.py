"""P0-21 regression: server must refuse to start without required secrets.

The guard lives in ``server._require_secret``. To prove it fires against a
*clean* environment — production and CI supply configuration via environment
variables, not a checked-out ``.env`` — these tests set ``DMRV_DISABLE_DOTENV=1``
so a developer ``.env`` on disk cannot silently repopulate a deliberately-absent
variable (the exact bug that made the original test a no-op).
"""

import importlib
import sys

import pytest


def _reimport_server():
    sys.modules.pop("server", None)
    return importlib.import_module("server")


def test_server_refuses_to_import_without_hmac_secret(monkeypatch):
    monkeypatch.setenv("DMRV_DISABLE_DOTENV", "1")
    monkeypatch.delenv("DMRV_HMAC_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="DMRV_HMAC_SECRET"):
        _reimport_server()


def test_server_refuses_to_import_without_admin_secret(monkeypatch):
    # HMAC present so the ADMIN guard is the one that must fire.
    monkeypatch.setenv("DMRV_DISABLE_DOTENV", "1")
    monkeypatch.setenv("DMRV_HMAC_SECRET", "test-secret")
    monkeypatch.delenv("DMRV_ADMIN_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="DMRV_ADMIN_SECRET"):
        _reimport_server()


def test_server_accepts_explicit_hmac_secret(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_SECRET", "test-secret-not-default")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DMRV_SKIP_MIGRATIONS", "1")
    try:
        server = _reimport_server()
        assert server._HMAC_SECRET == "test-secret-not-default"
    finally:
        # Restore the shared test secret and re-import so we don't leak a
        # module built with a one-off secret to the rest of the suite.
        monkeypatch.setenv("DMRV_HMAC_SECRET", "test-secret")
        _reimport_server()
