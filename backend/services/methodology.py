"""PR-4 — methodology as a first-class switch (CSI *and* Rainbow, for real).

Before this Part, every batch was gated by Rainbow's full C0-C10 rule set,
computed with CSI-3.2 math, and exported as JSON + a label — one path
wearing two names. This module makes methodology select the GATE SET (LCA
params + report format are selected elsewhere, reusing the existing
RegistryConfig / export-service rails).

Pure, no DB/HTTP — mirrors services/dispatch_state.py's shape.
"""

from __future__ import annotations

CSI = "CSI"
RAINBOW = "RAINBOW"
DEFAULT = "DEFAULT"

_METHODOLOGIES = (CSI, RAINBOW, DEFAULT)


def resolve_methodology(methodology_version: str | None) -> str:
    """Resolve a RegistryConfig.methodology_version string to CSI, RAINBOW,
    or DEFAULT. DEFAULT covers every existing project (no explicit
    methodology_version, or one that names neither known methodology) —
    the grandfather case that must reproduce exactly today's behavior."""
    if not methodology_version:
        return DEFAULT
    lowered = methodology_version.lower()
    if "csi" in lowered:
        return CSI
    if "rainbow" in lowered:
        return RAINBOW
    return DEFAULT


def gate_set_for(methodology: str) -> tuple[str, ...]:
    """The ordered set of gate CATEGORIES that apply for a methodology.

    Today's only category beyond the always-on core corroboration
    (yield/temp/transport/lab/moisture/pyrolysis-photo/flame/ignition/
    composite-sample/delivery/buyer — all wired unconditionally in
    corroboration.assemble/credit_engine, not methodology-conditional, since
    they are basic MRV data quality any methodology needs) is "c10_extras":
    the Rainbow-labeled C1/C8/C9/C10 issuance-gate signals (biomass method,
    kiln registration, scale/density calibration, annual methane, PAH,
    sampling cadence, cross-field plausibility) added in Rainbow-specific
    Parts of this codebase.

    RAINBOW and DEFAULT (grandfather) both include "c10_extras" — DEFAULT
    must reproduce today's exact behavior, which already applies the full
    Rainbow set to every batch regardless of project.

    CSI excludes "c10_extras": none of those Rainbow-labeled items have been
    confirmed against the actual CSI-3.2 methodology text (see
    docs/PATH_TO_ISSUANCE.md P0.1 — that confirmation is a standing,
    external, not-yet-done process item). Per this Part's explicit
    instruction not to invent CSI rules, CSI's gate set is deliberately
    smaller rather than guessing which subset CSI requires.
    TODO(methodology): once P0.1's conformance mapping exists, revisit
    whether any specific c10_extras item (e.g. sampling cadence, which is
    already phrased in generic methodology terms) should move into CSI's
    gate set on its own, individually-confirmed merit.
    """
    if methodology not in _METHODOLOGIES:
        raise ValueError(f"unknown methodology '{methodology}'")
    if methodology == CSI:
        return ()
    return ("c10_extras",)
