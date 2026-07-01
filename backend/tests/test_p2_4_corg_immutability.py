import pytest
from lca_engine import CORG_TABLE


def test_corg_table_immutability():
    # Attempting to assign to MappingProxyType should raise a TypeError
    with pytest.raises(TypeError):
        CORG_TABLE["Wood_chips"] = 0.99

    # Attempting to add a new key should raise a TypeError
    with pytest.raises(TypeError):
        CORG_TABLE["Hacked"] = 1.0

    # Verify that the value hasn't changed
    assert CORG_TABLE["Wood_chips"] == 0.55
