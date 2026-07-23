"""FM-0 — feedstock positive-list gate.

lca_engine.get_corg(species, corg_table) silently returns the table's
"Default" Corg value for ANY species not present in the table — correct for
get_corg itself (other call sites + the CSI-3.2 regression guarantee depend
on that exact fallback), but wrong as a *credit-integrity* policy: a typo'd
or unconfigured feedstock would otherwise silently mint a credit at the
wrong carbon value, with no error and no flag.

This module is the gate that turns "species not in the positive list" into
an explicit, reason-coded, provisional signal instead — mirrors
services/methodology.py's shape (pure, no DB/HTTP).
"""

from __future__ import annotations

from typing import Mapping, Optional


def derive_feedstock_compliance(
    feedstock_species: Optional[str],
    corg_table: Mapping[str, float],
    *,
    enforced: bool = True,
) -> tuple[bool, Optional[str]]:
    """(ok, reason) — ok unless `feedstock_species` (case-insensitively) is
    absent from `corg_table`'s real entries. The literal "Default" key is the
    fallback marker, not a valid species choice, so it never counts as a
    match. `enforced=False` is an inert override (mirrors every other
    deriver's `enforced` kwarg) for callers/tests that want to opt out."""
    if not enforced:
        return True, None
    if not feedstock_species:
        return False, "feedstock_not_in_positive_list"
    valid = {k.casefold() for k in corg_table if k.casefold() != "default"}
    if feedstock_species.casefold() not in valid:
        return False, "feedstock_not_in_positive_list"
    return True, None


def positive_list(corg_table: Mapping[str, float]) -> list[str]:
    """The table's real species keys (excludes the "Default" fallback
    marker), sorted for stable, deterministic output."""
    return sorted(k for k in corg_table if k.casefold() != "default")
