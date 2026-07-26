"""M0.2 — per-org feature flags (adapted to AppConfig.flags_json; see M0.1 NOTES)."""
import json

import pytest

from feature_flags import flag_enabled
from models import AppConfig


async def _set_flags(session_factory, flags: dict) -> None:
    async with session_factory() as s:
        s.add(AppConfig(config_id="default", flags_json=json.dumps(flags)))
        await s.commit()


@pytest.mark.asyncio
async def test_unknown_flag_raises(session_factory):
    async with session_factory() as s:
        with pytest.raises(ValueError):
            await flag_enabled(s, "not_a_real_flag")


@pytest.mark.asyncio
async def test_default_off_when_unconfigured(session_factory):
    async with session_factory() as s:
        assert await flag_enabled(s, "telemetry_v2") is False
        assert await flag_enabled(s, "telemetry_v2", "org-1") is False


@pytest.mark.asyncio
async def test_global_on(session_factory):
    await _set_flags(session_factory, {"ff.telemetry_v2": "on"})
    async with session_factory() as s:
        assert await flag_enabled(s, "telemetry_v2") is True
        assert await flag_enabled(s, "telemetry_v2", "org-1") is True


@pytest.mark.asyncio
async def test_org_override_beats_global(session_factory):
    await _set_flags(
        session_factory,
        {"ff.telemetry_v2": "on", "ff.telemetry_v2.org-x": "off"},
    )
    async with session_factory() as s:
        # org-x explicitly off overrides the global on
        assert await flag_enabled(s, "telemetry_v2", "org-x") is False
        # org-y has no override → falls back to global on
        assert await flag_enabled(s, "telemetry_v2", "org-y") is True
