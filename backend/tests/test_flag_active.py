"""H2 - opt-in vs opt-out flag semantics."""
import json
import pytest
from models import AppConfig
from feature_flags import flag_active, flag_enabled

pytestmark = pytest.mark.asyncio


async def _set(session_factory, d):
    async with session_factory() as s:
        row = await s.get(AppConfig, "default")
        if row is None:
            row = AppConfig(config_id="default")
            s.add(row)
        row.flags_json = json.dumps(d)
        await s.commit()


async def test_optout_defaults_on(session_factory):
    async with session_factory() as s:
        assert await flag_active(s, "timeline_v2") is True
        assert await flag_active(s, "ledgers_v2") is True


async def test_optin_defaults_off(session_factory):
    async with session_factory() as s:
        assert await flag_active(s, "telemetry_v2") is False


async def test_explicit_off_hides_optout(session_factory):
    await _set(session_factory, {"ff.timeline_v2": "off"})
    async with session_factory() as s:
        assert await flag_active(s, "timeline_v2") is False


async def test_org_override_beats_global(session_factory):
    await _set(session_factory, {"ff.ledgers_v2": "off", "ff.ledgers_v2.org-1": "on"})
    async with session_factory() as s:
        assert await flag_active(s, "ledgers_v2", "org-1") is True
        assert await flag_active(s, "ledgers_v2", "org-2") is False


async def test_flag_enabled_unchanged(session_factory):
    async with session_factory() as s:
        assert await flag_enabled(s, "timeline_v2") is False  # opt-in helper stays default-off
