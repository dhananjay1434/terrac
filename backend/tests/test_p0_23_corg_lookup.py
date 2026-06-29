"""P0-23 regression: get_corg must be case-insensitive and whitespace-tolerant."""
import pytest
from lca_engine import get_corg, CORG_TABLE


@pytest.mark.parametrize("variant", [
    "Lantana_camara",
    "lantana_camara",
    "LANTANA_CAMARA",
    " Lantana_camara ",
    "  lantana_camara\t",
])
def test_lantana_variants_resolve_to_060(variant):
    assert get_corg(variant) == pytest.approx(0.60)


def test_unknown_species_falls_back_to_default():
    assert get_corg("Unobtanium") == CORG_TABLE["Default"]


def test_empty_string_falls_back_to_default():
    assert get_corg("") == CORG_TABLE["Default"]


def test_none_falls_back_to_default():
    # Some legacy callers pass None
    assert get_corg(None) == CORG_TABLE["Default"]  # type: ignore[arg-type]


def test_corg_table_is_immutable():
    # P2-4 — must be MappingProxyType
    with pytest.raises(TypeError):
        CORG_TABLE["Hacked"] = 9.99  # type: ignore[index]
