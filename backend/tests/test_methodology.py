"""PR-4.1 — methodology resolver + gate-set selector (pure, no DB).

The DEFAULT case (no project, no registry_config, or an unrecognized
methodology_version string) MUST reproduce exactly today's behavior: every
existing project, having never set an explicit methodology, keeps the full
Rainbow C0-C10 gate set + CSI-3.2 math — nothing changes for it. This is the
explicit regression/grandfather guarantee this Part promises.
"""

from services.methodology import CSI, DEFAULT, RAINBOW, gate_set_for, resolve_methodology


def test_resolve_none_is_default():
    assert resolve_methodology(None) == DEFAULT


def test_resolve_empty_string_is_default():
    assert resolve_methodology("") == DEFAULT


def test_resolve_csi_case_insensitive():
    assert resolve_methodology("CSI-3.2") == CSI
    assert resolve_methodology("csi-3.2") == CSI
    assert resolve_methodology("Csi Artisan C-Sink") == CSI


def test_resolve_rainbow_case_insensitive():
    assert resolve_methodology("Rainbow") == RAINBOW
    assert resolve_methodology("rainbow-v1") == RAINBOW


def test_resolve_unrecognized_string_is_default():
    assert resolve_methodology("some-other-registry-v1") == DEFAULT


def test_gate_set_default_includes_c10_extras():
    """DEFAULT must match RAINBOW's gate set exactly — the regression pin."""
    assert gate_set_for(DEFAULT) == gate_set_for(RAINBOW)
    assert "c10_extras" in gate_set_for(DEFAULT)


def test_gate_set_rainbow_includes_c10_extras():
    assert "c10_extras" in gate_set_for(RAINBOW)


def test_gate_set_csi_excludes_unconfirmed_c10_extras():
    """No invented CSI rules: the Rainbow-labeled C10 extras (C1 biomass, C4
    composite, C5 delivery/buyer, C8 kiln/scale/density calibration, C9
    methane/PAH, plausibility) have not been confirmed as CSI-3.2
    requirements, so CSI's gate set excludes them rather than guessing."""
    assert "c10_extras" not in gate_set_for(CSI)


def test_gate_set_unknown_methodology_raises():
    import pytest

    with pytest.raises(ValueError):
        gate_set_for("bogus")
