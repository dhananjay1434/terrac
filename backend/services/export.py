"""Export projections for CSI and Rainbow registries.

Schema-accurate against the recovered CSI GlobalCSinkVerificationReport field set
(EXECUTION_MASTER_PLAN E11/E23). Admin-gated at the router layer.
"""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import (
    Batch,
    CreditIssuance,
    MoistureReading,
    CompositePileSample,
    TransportEvent,
    MediaFile,
)
from jsonsafe import _safe_json
from settings import log


async def _load_child_payloads(session: AsyncSession, model, batch_uuid: str) -> list[dict]:
    rows = (
        await session.execute(select(model).where(model.batch_uuid == batch_uuid))
    ).scalars().all()
    out = []
    for r in rows:
        d = _safe_json(r.payload_json, context=f"{model.__tablename__} {r.batch_uuid}")
        out.append(d if isinstance(d, dict) else {"_raw": d})
    return out


async def export_batch_common(batch: Batch, session: AsyncSession) -> Dict[str, Any]:
    """Shared, schema-accurate projection of an issuable batch."""
    if batch.provisional:
        reasons = _safe_json(batch.provisional_reasons, context=f"reasons {batch.batch_uuid}")
        raise ValueError(f"batch_provisional:{reasons if isinstance(reasons, list) else []}")

    # Audit fix 8: a non-provisional batch always carries an issuance signature
    # (recompute nulls it on provisional rows). Its absence at export time means
    # the row was tampered or corrupted — refuse to emit a registry report.
    if not batch.lca_signature:
        raise ValueError("unsigned_batch")

    moisture = await _load_child_payloads(session, MoistureReading, batch.batch_uuid)
    composite = await _load_child_payloads(session, CompositePileSample, batch.batch_uuid)
    transport = await _load_child_payloads(session, TransportEvent, batch.batch_uuid)

    media_rows = (
        await session.execute(
            select(MediaFile).where(MediaFile.batch_uuid == batch.batch_uuid)
        )
    ).scalars().all()

    # PR-1: trace the export to its ledger serial when one exists — a batch
    # can be exported (non-provisional + signed) before it has an issuance
    # record, so this is optional/absent, not required.
    issuance_row = (
        await session.execute(
            select(CreditIssuance).where(CreditIssuance.batch_uuid == batch.batch_uuid)
        )
    ).scalar_one_or_none()
    issuance = (
        {
            "serial": issuance_row.serial,
            "vintage": issuance_row.vintage,
            "status": issuance_row.status,
            "t_co2e_frozen": issuance_row.t_co2e_frozen,
            "issued_at": issuance_row.issued_at.isoformat()
            if issuance_row.issued_at
            else None,
            "registry_submission_ref": issuance_row.registry_submission_ref,
        }
        if issuance_row is not None
        else None
    )

    return {
        "batch_uuid": str(batch.batch_uuid),
        "project_id": batch.project_id,
        "scale_id": batch.scale_id,
        "feedstock_species": batch.feedstock_species,
        "harvest_timestamp": batch.harvest_timestamp.isoformat() if batch.harvest_timestamp else None,
        "location": {"latitude": batch.latitude, "longitude": batch.longitude},
        "inputs": {
            "wet_yield_kg": batch.wet_yield_kg,
            "moisture_percent": batch.moisture_percent,
            "biomass_input_kg": batch.biomass_input_kg,
            "biomass_measurement_method": batch.biomass_measurement_method,
            "min_recorded_temp_c": batch.min_recorded_temp_c,
            "transport_distance_km": batch.transport_distance_km,
        },
        "lab": {
            "lab_h_corg": batch.lab_h_corg,
            "organic_carbon_pct": batch.organic_carbon_pct,
        },
        "moisture_readings": moisture,
        "composite_samples": composite,
        "transport_events": transport,
        "evidence_media": [
            {
                "operation_id": m.operation_id,
                "sha256_hash": m.sha256_hash,
                "capture_type": m.capture_type,
                "capture_type_verified": bool(m.capture_type_verified),
                "exif_lat": m.exif_lat,
                "exif_lon": m.exif_lon,
                "uploaded_at": m.uploaded_at.isoformat() if m.uploaded_at else None,
            }
            for m in media_rows
        ],
        "credit": {
            "net_credit_t_co2e": batch.net_credit_t_co2e,
            "lca_signature": batch.lca_signature,
            "lca_signature_key_id": batch.lca_signature_key_id,
            "lca_methodology_version": batch.lca_methodology_version,
            "lca_audit": _safe_json(batch.lca_audit_json, context=f"lca_audit {batch.batch_uuid}"),
        },
        "status": batch.status,
        "provisional": batch.provisional,
        "issuance": issuance,
        # Stamped in the route so tests can assert equality deterministically.
        "exported_at": None,
    }


class CSIExportService:
    @staticmethod
    async def export_batch_as_csi(batch: Batch, session: AsyncSession) -> Dict[str, Any]:
        common = await export_batch_common(batch, session)
        common["standard"] = "CSI GlobalCSinkVerificationReport v1"
        log.info(f"[CSI Export] batch={batch.batch_uuid}")
        return common


class RainbowExportService:
    @staticmethod
    async def export_batch_as_rainbow(batch: Batch, session: AsyncSession) -> Dict[str, Any]:
        common = await export_batch_common(batch, session)
        common["standard"] = "Rainbow Biochar Standard (Distributed Closed-Kiln)"
        # ICVCM headline field: prefer measured lab H:Corg, else organic carbon fraction.
        common["h_corg_ratio"] = (
            batch.lab_h_corg if batch.lab_h_corg is not None else batch.organic_carbon_pct
        )
        log.info(f"[Rainbow Export] batch={batch.batch_uuid}")
        return common
