"""FM-0 — pure feedstock positive-list gate.

lca_engine.get_corg silently falls back to the "Default" Corg value for ANY
species not in the table — no error, no flag. That is correct for get_corg
itself (other call sites + the CSI-3.2 regression guarantee depend on it),
but credit_engine's recompute must not let an unknown/misconfigured species
silently mint a credit at the wrong carbon value. derive_feedstock_compliance
is the gate that turns "not in the table" into a provisional reason instead.
"""

from services.feedstock import derive_feedstock_compliance, positive_list


_TABLE = {
    "Lantana_camara": 0.60,
    "Wood_chips": 0.55,
    "Agricultural_waste": 0.50,
    "Default": 0.55,
}


class TestDeriveFeedstockCompliance:
    def test_known_species_is_compliant(self):
        assert derive_feedstock_compliance("Lantana_camara", _TABLE) == (True, None)

    def test_known_species_case_insensitive(self):
        assert derive_feedstock_compliance("lantana_camara", _TABLE) == (True, None)
        assert derive_feedstock_compliance("WOOD_CHIPS", _TABLE) == (True, None)

    def test_unknown_species_is_flagged(self):
        assert derive_feedstock_compliance("Made_up_grass", _TABLE) == (
            False,
            "feedstock_not_in_positive_list",
        )

    def test_empty_species_is_flagged(self):
        assert derive_feedstock_compliance("", _TABLE) == (
            False,
            "feedstock_not_in_positive_list",
        )

    def test_none_species_is_flagged(self):
        assert derive_feedstock_compliance(None, _TABLE) == (
            False,
            "feedstock_not_in_positive_list",
        )

    def test_the_literal_default_key_itself_is_not_a_valid_species(self):
        # "Default" is the fallback marker, not a real feedstock choice.
        assert derive_feedstock_compliance("Default", _TABLE) == (
            False,
            "feedstock_not_in_positive_list",
        )

    def test_unenforced_is_always_compliant(self):
        assert derive_feedstock_compliance(
            "Made_up_grass", _TABLE, enforced=False
        ) == (True, None)
        assert derive_feedstock_compliance(None, _TABLE, enforced=False) == (
            True,
            None,
        )


class TestPositiveList:
    def test_returns_sorted_keys_excluding_default(self):
        assert positive_list(_TABLE) == [
            "Agricultural_waste",
            "Lantana_camara",
            "Wood_chips",
        ]

    def test_empty_table_returns_empty_list(self):
        assert positive_list({}) == []

    def test_table_with_only_default_returns_empty_list(self):
        assert positive_list({"Default": 0.55}) == []
