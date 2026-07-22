"""V8 Part 4 (F) — bulk-density volume→mass math.

Pure function only (no DB/HTTP): artisanal biochar can't go on a truck scale
mid-process, so an alternate yield-mass path is volume (kiln_gross_capacity,
already captured in pyrolysis telemetry) × a calibrated bulk density.
"""

from __future__ import annotations


def volume_to_mass_kg(volume_l: float, density_kg_per_l: float) -> float:
    """mass_kg = volume_l * density_kg_per_l. Raises ValueError on a
    non-positive input — a zero/negative volume or density is a data error,
    never silently coerced to zero mass."""
    if volume_l <= 0:
        raise ValueError(f"volume_l must be positive, got {volume_l}")
    if density_kg_per_l <= 0:
        raise ValueError(f"density_kg_per_l must be positive, got {density_kg_per_l}")
    return volume_l * density_kg_per_l


def mass_and_volume_to_density_kg_per_l(mass_kg: float, volume_l: float) -> float:
    """Deferred R3 — the inverse of volume_to_mass_kg: a device-recorded
    calibration test reports the sample's mass + volume, and the SERVER (not
    the submitting device) computes the authoritative density from them —
    the device's own display-only computation is never trusted as the
    stored value. Raises ValueError on a non-positive input, same
    data-error posture as volume_to_mass_kg."""
    if mass_kg <= 0:
        raise ValueError(f"mass_kg must be positive, got {mass_kg}")
    if volume_l <= 0:
        raise ValueError(f"volume_l must be positive, got {volume_l}")
    return mass_kg / volume_l
