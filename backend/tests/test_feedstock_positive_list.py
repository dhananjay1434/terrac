"""FM-0 — pure feedstock positive-list gate.

lca_engine.get_corg silently falls back to the "Default" Corg value for ANY
species not in the table — no error, no flag. That is correct for get_corg
itself (other call sites + the CSI-3.2 regression guarantee depend on it),
but credit_engine's recompute must not let an unknown/misconfigured species
silently mint a credit at the wrong carbon value. derive_feedstock_compliance
is the gate that turns "not in the table" into a provisional reason instead.
"""

import pytest

from schemas import BatchPayload
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


class TestBatchPayloadIntakeValidator:
    """FM-1 — the intake validator is project-blind (no DB access, can't see
    project_id) so it can no longer check CORG_TABLE membership (that would
    wrongly reject a valid per-project custom feedstock). It's now a basic
    presence check; the real, project-aware enforcement is
    derive_feedstock_compliance in the recompute path (tested above)."""

    def _payload(self, **over):
        base = dict(
            batch_uuid="b" * 36,
            feedstock_species="Some_arbitrary_species",
            harvest_timestamp="2026-07-01T00:00:00Z",
            moisture_percent=12.0,
        )
        base.update(over)
        return base

    def test_arbitrary_non_default_species_is_accepted_at_intake(self):
        # Would have been rejected by the old CORG_TABLE-membership check.
        payload = BatchPayload(**self._payload())
        assert payload.feedstock_species == "Some_arbitrary_species"

    def test_known_species_still_accepted(self):
        payload = BatchPayload(**self._payload(feedstock_species="Lantana_camara"))
        assert payload.feedstock_species == "Lantana_camara"

    def test_empty_species_rejected(self):
        with pytest.raises(ValueError):
            BatchPayload(**self._payload(feedstock_species=""))

    def test_whitespace_only_species_rejected(self):
        with pytest.raises(ValueError):
            BatchPayload(**self._payload(feedstock_species="   "))


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
