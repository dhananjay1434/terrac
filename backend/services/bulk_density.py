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
