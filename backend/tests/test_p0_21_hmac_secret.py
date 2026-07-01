"""P0-21 regression: server must refuse to start without DMRV_HMAC_SECRET."""

import importlib
import os
import sys

import pytest


def test_server_refuses_to_import_without_hmac_secret(monkeypatch):
    # Remove the env var
    monkeypatch.delenv("DMRV_HMAC_SECRET", raising=False)
    # Force re-import of server module
    sys.modules.pop("server", None)
    with pytest.raises(RuntimeError, match="DMRV_HMAC_SECRET"):
        importlib.import_module("server")


def test_server_accepts_explicit_hmac_secret(monkeypatch):
    monkeypatch.setenv("DMRV_HMAC_SECRET", "test-secret-not-default")
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("DMRV_SKIP_MIGRATIONS", "1")
    sys.modules.pop("server", None)
    try:
        server = importlib.import_module("server")
        assert server._HMAC_SECRET == "test-secret-not-default"
    finally:
        # Restore original env var and re-import so we don't leak state to other tests
        monkeypatch.setenv("DMRV_HMAC_SECRET", "test-secret")
        sys.modules.pop("server", None)
        importlib.import_module("server")
