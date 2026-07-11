"""CSI Global Artisan C-Sink — 8-Step LCA Engine.

Implements the exact mathematical pipeline mandated by the Carbon Standards
International (CSI) Global Artisan C-Sink methodology for biochar carbon
credit calculation.

References:
  - Global Biochar C-Sink Standard 3.2 (carbon-standards.com/4000039EN.pdf)
  - Collection of formulas and emission factors (4000115EN.pdf)

Every function is pure, stateless, and independently testable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Mapping
from types import MappingProxyType


# ==================== CSI Constants ====================

METHODOLOGY_VERSION = "CSI-3.2"


# Total Organic Carbon (Corg) by feedstock species — CSI registry values.
_CORG_RAW: Dict[str, float] = {
    "Lantana_camara": 0.60,  # 60% Corg — CSI positive-list value
    "Wood_chips": 0.55,
    "Agricultural_waste": 0.50,
    "Default": 0.55,
}
CORG_TABLE: Mapping[str, float] = MappingProxyType(_CORG_RAW)
_CORG_LOOKUP_CI = {k.casefold(): v for k, v in _CORG_RAW.items()}

# Stoichiometric ratio: elemental C → CO₂e
CO2_PER_C = 44.0 / 12.0  # ≈ 3.6667

# Margin of Safety — CSI mandatory universal deduction (kg CO₂e per tonne dry mass)
SAFETY_DEDUCTION_KG_PER_T = 20.0

# Transport diesel emission factor: 11.94 g CO₂e per tonne-km  →  0.01194 kg
TRANSPORT_FACTOR_KG_PER_T_KM = 0.01194

# Transport penalty threshold
TRANSPORT_THRESHOLD_KM = 100.0

# Methane penalties (kg CO₂e per tonne dry mass)
CH4_COMPLIANT_KG_PER_T = 0.005  # moisture < 15% AND min_temp > 190°C
CH4_NON_COMPLIANT_KG_PER_T = 30.0  # default heavy penalty


# ==================== Data Classes ====================


@dataclass
class LCAAudit:
    """Full audit trail returned by the LCA engine."""

    methodology_version: str

    # Inputs
    wet_yield_kg: float
    moisture_percent: float
    min_recorded_temp_c: float
    transport_distance_km: float
    corg_pct: float

    # Step 1
    dry_mass_t: float

    # Step 2 — informational only; NOT used in net credit issuance (issuance
    # derives from `cremain` in Steps 3/8).
    gross_c_sink_t_co2e: float

    # Step 3
    cremain_t: float

    # Step 4
    safety_deduction_kg: float

    # Step 5-6
    transport_penalty_kg: float

    # Step 7
    ch4_compliant: bool
    ch4_penalty_kg: float

    # Step 8
    net_credit_t_co2e: float

    # True when the credit used an ASSUMED H:Corg (no lab value supplied).
    # A provisional credit must never be issued as final.
    provisional: bool = True

    # C7: True when corg_pct came from the species CONSTANT (CORG_TABLE) rather
    # than a lab-measured organic-carbon value. Like `provisional` for H:Corg,
    # an assumed-Corg credit must not be issued as final.
    corg_assumed: bool = True

    audit_signature: str | None = None


# ==================== Core Functions ====================


def get_corg(feedstock_species: str) -> float:
    """Look up the Total Organic Carbon fraction for a feedstock species."""
    key = (feedstock_species or "").strip()
    return _CORG_LOOKUP_CI.get(key.casefold(), CORG_TABLE["Default"])


def step1_dry_mass(wet_yield_kg: float, moisture_percent: float) -> float:
    """Step 1 — Yield Mass Balance.

    Formula: dry_mass_t = (wet_yield_kg * (1 - moisture_pct / 100)) / 1000
    """
    return (wet_yield_kg * (1.0 - moisture_percent / 100.0)) / 1000.0


def step2_gross_c_sink(corg_pct: float, dry_mass_t: float) -> float:
    """Step 2 — Gross C-Sink.

    Formula: gross_c_sink = Corg_pct * dry_mass_t * (44/12)
    """
    return corg_pct * dry_mass_t * CO2_PER_C


def step3_cremain(
    dry_mass_t: float, corg_pct: float, *, h_corg_ratio: float, t: int = 100
) -> float:
    """Step 3 — H:Corg 100-year Decay Function.

    If H:Corg < 0.4 (top-tier stability):
      Cremain = MBC * Ccont * (0.75 + 0.25 * (
          0.1787 * e^(-0.5337 * t) + 0.8237 * e^(-0.00997 * t)))

    For Lantana biochar, H:Corg is typically 0.3–0.35 (always < 0.4).
    """
    if h_corg_ratio is None:
        raise ValueError("h_corg_ratio is required (lab-measured H:Corg).")
    if h_corg_ratio >= 0.4:
        # Lower-tier permanence — conservative 70% retention
        return dry_mass_t * corg_pct * 0.70

    decay_term = 0.1787 * math.exp(-0.5337 * t) + 0.8237 * math.exp(-0.00997 * t)
    return dry_mass_t * corg_pct * (0.75 + 0.25 * decay_term)


def step4_safety_deduction(dry_mass_t: float) -> float:
    """Step 4 — Margin of Security.

    Formula: safety_deduction = dry_mass_t * 20 (kg CO₂e)
    Mandatory universal deduction applied to all batches.
    """
    return dry_mass_t * SAFETY_DEDUCTION_KG_PER_T


def step5_6_transport_penalty(transport_distance_km: float, dry_mass_t: float) -> float:
    """Steps 5 & 6 — Transport Distance + Penalty.

    If distance > 100 km:
      transport_penalty = distance_km * 0.01194 * dry_mass_t (kg CO₂e)
    Else: 0
    """
    if transport_distance_km <= TRANSPORT_THRESHOLD_KM:
        return 0.0
    return transport_distance_km * TRANSPORT_FACTOR_KG_PER_T_KM * dry_mass_t


def step7_ch4_penalty(
    dry_mass_t: float,
    moisture_percent: float,
    min_recorded_temp_c: float,
) -> tuple[bool, float]:
    """Step 7 — Algorithmic Methane Adjustment.

    If min_temp > 190°C AND moisture < 15%:
      ch4_penalty = dry_mass_t * 0.005  (negligible — compliant burn)
    Else:
      ch4_penalty = dry_mass_t * 30     (heavy default penalty)

    Returns:
        (is_compliant, penalty_kg_co2e)
    """
    compliant = min_recorded_temp_c > 190.0 and moisture_percent < 15.0
    if compliant:
        return True, dry_mass_t * CH4_COMPLIANT_KG_PER_T
    return False, dry_mass_t * CH4_NON_COMPLIANT_KG_PER_T


def step8_net_credit(
    cremain_t_c: float,
    safety_kg: float,
    transport_kg: float,
    ch4_kg: float,
) -> float:
    """Step 8 — Net Credit.

    Formula (CSI Global Artisan C-Sink Standard 3.2):
      net_credit_t_co2e = (cremain_t_c * 44/12)
                          - (safety/1000) - (transport/1000) - (ch4/1000)

    `cremain_t_c` is tonnes of elemental carbon REMAINING after the 100-year
    H:Corg decay (Step 3). It must be converted to tonnes CO₂e here using
    the 44/12 stoichiometric ratio — this is the value that survives 100
    years and is the legitimate basis for issuance.

    All penalty inputs are in kg CO₂e; output is in tonnes CO₂e.
    """
    return (
        (cremain_t_c * CO2_PER_C)
        - (safety_kg / 1000.0)
        - (transport_kg / 1000.0)
        - (ch4_kg / 1000.0)
    )


# ==================== Main Entry Point ====================


def calculate_carbon_credit(
    wet_yield_kg: float,
    moisture_percent: float,
    min_recorded_temp_c: float = 0.0,
    transport_distance_km: float = 0.0,
    feedstock_species: str = "Lantana_camara",
    h_corg_ratio: float | None = None,
    corg_override: float | None = None,
) -> LCAAudit:
    """Execute the complete 8-step CSI LCA pipeline.

    Args:
        wet_yield_kg:          BLE crane scale reading (kg)
        moisture_percent:      Manual moisture meter reading (%)
        min_recorded_temp_c:   Minimum temperature from BLE thermocouple array (°C)
        transport_distance_km: Haversine GPS distance, production site → application field (km)
        feedstock_species:     CSI positive-list species key
        h_corg_ratio:          Lab-derived H:Corg molar ratio (default 0.35 for Lantana)
        corg_override:         Lab-measured organic-carbon fraction (0–1). When
                               supplied it REPLACES the species-constant CORG_TABLE
                               lookup (C7); when None the constant is used and the
                               result is marked corg_assumed (not issuable).

    Returns:
        LCAAudit dataclass with full calculation trail.
    """
    # C7: prefer a lab-measured Corg over the species constant. The constant was
    # the same class of self-asserted assumption as the old H:Corg — a lab value
    # is authoritative; its absence keeps the credit provisional (corg_assumed).
    corg_assumed = corg_override is None
    corg = get_corg(feedstock_species) if corg_override is None else corg_override

    # Phase 8: a credit computed without a lab-measured H:Corg is PROVISIONAL —
    # it falls back to the conservative 0.35 assumption but must never be
    # issued as final.
    provisional = h_corg_ratio is None
    h_corg_ratio = 0.35 if h_corg_ratio is None else h_corg_ratio

    # Step 1
    dry_mass = step1_dry_mass(wet_yield_kg, moisture_percent)

    # Step 2
    gross = step2_gross_c_sink(corg, dry_mass)

    # Step 3
    cremain = step3_cremain(dry_mass, corg, t=100, h_corg_ratio=h_corg_ratio)

    # Step 4
    safety = step4_safety_deduction(dry_mass)

    # Steps 5-6
    transport = step5_6_transport_penalty(transport_distance_km, dry_mass)

    # Step 7
    ch4_ok, ch4 = step7_ch4_penalty(dry_mass, moisture_percent, min_recorded_temp_c)

    # Step 8 — net credit derived from `cremain` (Step 3), NOT from raw gross.
    net = step8_net_credit(cremain, safety, transport, ch4)

    return LCAAudit(
        methodology_version=METHODOLOGY_VERSION,
        wet_yield_kg=wet_yield_kg,
        moisture_percent=moisture_percent,
        min_recorded_temp_c=min_recorded_temp_c,
        transport_distance_km=transport_distance_km,
        corg_pct=corg,
        dry_mass_t=dry_mass,
        gross_c_sink_t_co2e=gross,
        cremain_t=cremain,
        safety_deduction_kg=safety,
        transport_penalty_kg=transport,
        ch4_compliant=ch4_ok,
        ch4_penalty_kg=ch4,
        net_credit_t_co2e=net,
        provisional=provisional,
        corg_assumed=corg_assumed,
    )


import json
import hmac
import hashlib


def sign_lca_audit(audit: LCAAudit, secret: str, *, batch_uuid: str) -> str:
    """Sign the LCA audit using HMAC SHA-256, bound to the batch identity.

    Phase 15-B: the signature MUST include `batch_uuid` so two batches with
    identical physical inputs do NOT produce the same signature (which previously
    allowed cross-batch replay of an issuance signature). `batch_uuid` is required
    keyword-only — callers cannot forget it.
    """
    # Deterministic dict of the physical audit (minus the signature field) + the
    # batch identity that scopes this signature to exactly one minting event.
    payload_str = _lca_sign_payload(audit, batch_uuid=batch_uuid)
    signature = hmac.new(
        secret.encode(), payload_str.encode(), hashlib.sha256
    ).hexdigest()
    audit.audit_signature = signature
    return signature


def _lca_sign_payload(audit: "LCAAudit", *, batch_uuid: str) -> str:
    """The exact deterministic string sign_lca_audit HMACs. Factored out so
    verification (P3.6) reconstructs the identical payload."""
    data = {k: v for k, v in audit.__dict__.items() if k != "audit_signature"}
    data["batch_uuid"] = str(batch_uuid)
    return json.dumps(data, sort_keys=True)


def lca_sign_payload_bytes(audit: "LCAAudit", *, batch_uuid: str) -> bytes:
    """Public helper: the signable bytes for an audit (used by hmac_keys.sign/
    verify so the versioned-key path signs the same payload as sign_lca_audit)."""
    return _lca_sign_payload(audit, batch_uuid=batch_uuid).encode()
