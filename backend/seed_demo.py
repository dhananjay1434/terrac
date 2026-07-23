"""Demo seed — fresh, schema-current dmrv.db for the client demo.

Run from backend/ with the demo secrets + DATABASE_URL in env (see the
invocation in the demo prep). Produces:
  • RegistryConfig 'csi-default'  (corg_table → feedstock positive list)
  • Project 'demo-lantana-01'      (allowed_feedstocks=['Lantana_camara'],
                                    client_target=25) — the app resolves its
                                    feedstock from THIS at runtime (FM-2/FM-4)
  • a portal admin user            (demo@terracipher.local / demo-pass-12345)
  • a registered Kiln
  • a HERO batch (fully compliant → ISSUABLE, all-green checklist) with dummy
    evidence images — the Act-3 finale
  • two PROVISIONAL batches under demo-lantana-01 (incomplete) — the "the
    system won't call it issued until every gate passes" story

Authentic: drives the REAL recompute pipeline (no faked compliance flags).
Idempotent-ish: it recreates a fresh DB, so run against a NON-production file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv


def _dummy_jpeg(color: tuple[int, int, int]) -> bytes:
    """A small valid JPEG so the verifier UI can render a real thumbnail.
    Uses Pillow if available, else a tiny embedded 1x1 JPEG."""
    try:
        import io

        from PIL import Image  # type: ignore

        img = Image.new("RGB", (320, 240), color)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        return buf.getvalue()
    except Exception:
        # Minimal valid 1x1 red JPEG.
        import base64

        return base64.b64decode(
            "/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAP//////////////////////////////"
            "////////////////////////////////////////////////////wgALCAABAAEB"
            "AREA/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA=/9k="
        )


async def main() -> None:
    from db import engine, init_db
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from credit_engine import recompute_batch_credit
    from models import (
        Batch,
        CompositePileSample,
        EndUseApplication,
        Kiln,
        MediaFile,
        MoistureReading,
        PortalUser,
        Project,
        PyrolysisTelemetry,
        RegistryConfig,
        YieldMetrics,
    )
    from portal.auth import hash_password
    from storage import get_storage

    # 1. Fresh schema at head.
    await init_db()

    Session = async_sessionmaker(engine, expire_on_commit=False)
    storage = get_storage()

    now = datetime.now(timezone.utc)
    sha = "a" * 64  # placeholder evidence hash (real captures compute their own)

    CORG_TABLE = {
        "Lantana_camara": 0.60,
        "Wood_chips": 0.55,
        "Agricultural_waste": 0.50,
        "Default": 0.55,
    }

    async with Session() as s:
        # --- RegistryConfig (defines the feedstock positive list) ------------
        s.add(
            RegistryConfig(
                config_id="csi-default",
                registry_name="Carbon Standards International",
                methodology_version="CSI-3.2",
                params_json=json.dumps({"corg_table": CORG_TABLE}),
            )
        )

        # --- Project the field app resolves its feedstock from ---------------
        s.add(
            Project(
                project_id="demo-lantana-01",
                name="Demo Biochar Project",
                registry_config_id="csi-default",
                allowed_feedstocks=json.dumps(["Lantana_camara"]),
                client_target=25,
            )
        )

        # --- Portal admin (to log into the verifier portal) ------------------
        s.add(
            PortalUser(
                email="demo@terracipher.local",
                password_hash=hash_password("demo-pass-12345"),
                role="admin",
                disabled=False,
            )
        )

        # --- Registered kiln (C8) -------------------------------------------
        s.add(
            Kiln(
                kiln_id="KILN-DEMO-01",
                material="steel",
                weight_kg=120.0,
                lifetime_years=10.0,
            )
        )
        await s.commit()

    # ---- helper: build one batch + its evidence, then recompute -------------
    async def _seed_batch(
        *,
        label: str,
        fully_compliant: bool,
        project_id: str | None,
        with_images: bool,
    ) -> str:
        buid = str(_uuid.uuid4())
        async with Session() as s:
            batch = Batch(
                batch_uuid=buid,
                operation_id=f"op-{label}-{buid[:8]}",
                feedstock_species="Lantana_camara",
                harvest_timestamp=now - timedelta(days=4),
                moisture_percent=12.0,
                harvest_uptime_seconds=100,
                device_id="demo-device",
                latitude=12.9716,
                longitude=77.5946,
                biomass_input_kg=500.0,
                biomass_measurement_method="direct_weigh",
                project_id=project_id,
            )
            if fully_compliant:
                # lab-measured permanence inputs → not provisional on those axes
                batch.lab_h_corg = 0.30
                batch.organic_carbon_pct = 0.60
            s.add(batch)

            # Telemetry (open kiln, 60 samples, flame + smoke evidence)
            tel = {
                "telemetry_uuid": str(_uuid.uuid4()),
                "batch_uuid": buid,
                "kiln_type": "open",
                "kiln_id": "KILN-DEMO-01",
                "kiln_gross_capacity": 1000.0,
                "burn_start_timestamp": (now - timedelta(hours=3)).isoformat(),
                "burn_end_timestamp": (now - timedelta(hours=1)).isoformat(),
                "temperature_readings": [650.0] * 60,
                "flame_height_m": 0.3,
                "smoke_evidence": [
                    {"stage": "flame_curtain", "sha256": sha},
                    {"stage": "quenching", "sha256": sha},
                    {"stage": "flame_height", "sha256": sha},
                ],
            }
            s.add(
                PyrolysisTelemetry(
                    telemetry_uuid=tel["telemetry_uuid"],
                    batch_uuid=buid,
                    payload_json=json.dumps(tel),
                )
            )

            if fully_compliant:
                # Yield
                s.add(
                    YieldMetrics(
                        yield_uuid=str(_uuid.uuid4()),
                        batch_uuid=buid,
                        payload_json=json.dumps(
                            {
                                "yield_uuid": str(_uuid.uuid4()),
                                "batch_uuid": buid,
                                "wet_yield_weight_kg": 100.0,
                            }
                        ),
                    )
                )
                # Application (delivery + buyer + gps)
                s.add(
                    EndUseApplication(
                        application_uuid=str(_uuid.uuid4()),
                        batch_uuid=buid,
                        payload_json=json.dumps(
                            {
                                "application_uuid": str(_uuid.uuid4()),
                                "batch_uuid": buid,
                                "latitude": 13.9716,
                                "longitude": 77.5946,
                                "delivery_date": (now - timedelta(hours=1)).isoformat(),
                                "delivered_amount_kg": 50.0,
                                "buyer_name": "Asha Farmers Co-op",
                            }
                        ),
                    )
                )
                # 10 moisture readings
                for i in range(1, 11):
                    s.add(
                        MoistureReading(
                            reading_uuid=str(_uuid.uuid4()),
                            batch_uuid=buid,
                            payload_json=json.dumps(
                                {
                                    "reading_uuid": str(_uuid.uuid4()),
                                    "batch_uuid": buid,
                                    "moisture_percent": 12.0,
                                    "sequence": i,
                                    "sha256_hash": sha,
                                }
                            ),
                        )
                    )
                # Composite sample
                s.add(
                    CompositePileSample(
                        sample_uuid=str(_uuid.uuid4()),
                        batch_uuid=buid,
                        payload_json=json.dumps(
                            {
                                "sample_uuid": str(_uuid.uuid4()),
                                "batch_uuid": buid,
                                "sha256_hash": sha,
                            }
                        ),
                    )
                )

            if with_images:
                for ct, color in [
                    ("batch_photo", (60, 110, 60)),
                    ("flame_curtain", (200, 90, 40)),
                    ("quenching", (60, 90, 160)),
                    ("flame_height", (150, 80, 40)),
                    ("post_burn_mass", (100, 100, 100)),
                ]:
                    op = f"media-{ct}-{buid[:8]}"
                    
                    asset_path = os.path.join(os.path.dirname(__file__), "demo_assets", f"{ct}.jpg")
                    if os.path.exists(asset_path):
                        with open(asset_path, "rb") as f:
                            content = f.read()
                    else:
                        content = _dummy_jpeg(color)
                        
                    import hashlib

                    key = storage.write(op, "demo-device", content)
                    s.add(
                        MediaFile(
                            batch_uuid=buid,
                            operation_id=op,
                            file_path=key,
                            sha256_hash=hashlib.sha256(content).hexdigest(),
                            filename=f"{ct}.jpg",
                            capture_type=ct,
                            capture_type_verified=True,
                            uploaded_at=now,
                        )
                    )

            await s.commit()

            # Recompute against the real pipeline (populates provisional/credit).
            await recompute_batch_credit(s, batch)
            await s.commit()
        return buid

    hero = await _seed_batch(
        label="hero", fully_compliant=True, project_id=None, with_images=True
    )
    prov1 = await _seed_batch(
        label="prov1", fully_compliant=False, project_id="demo-lantana-01", with_images=True
    )
    prov2 = await _seed_batch(
        label="prov2", fully_compliant=False, project_id="demo-lantana-01", with_images=False
    )

    # ---- Report ------------------------------------------------------------
    from sqlalchemy import select

    async with Session() as s:
        for tag, bu in [("HERO", hero), ("PROV1", prov1), ("PROV2", prov2)]:
            b = (
                await s.execute(select(Batch).where(Batch.batch_uuid == bu))
            ).scalar_one()
            print(
                f"{tag}: {bu}  provisional={b.provisional}  "
                f"credit={b.net_credit_t_co2e:.4f}  reasons={b.provisional_reasons}"
            )
    print("\nProject: demo-lantana-01  |  Portal admin: demo@terracipher.local / demo-pass-12345")
    print("SEED OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the DMRV database with demo data.")
    parser.add_argument(
        "--remote",
        type=str,
        help="Optional Render/Remote DATABASE_URL. If provided, seeds the remote DB instead of local.",
    )
    args = parser.parse_args()

    # If --remote is passed, force it into the environment before importing db.py
    if args.remote:
        print(f"Seeding REMOTE database: {args.remote.split('@')[-1]}")
        os.environ["DATABASE_URL"] = args.remote
    else:
        # Otherwise fallback to .env (which usually points to sqlite://)
        load_dotenv()
        print("Seeding LOCAL database from .env")

    asyncio.run(main())
