"""Rich, idempotent-safe demo seed — ADDS a multi-month spread of batches
through the REAL compute pipeline (no faked credit/compliance flags), so the
dashboard's credit chart, blocker histogram, and quality cards all have
enough variety to look populated for a demo.

Unlike seed_demo.py, this script is safe to run against a database that
already has the fixed reference rows (RegistryConfig 'csi-default', Project
'demo-lantana-01', Kiln 'KILN-DEMO-01', the demo portal user) — it looks
them up and reuses them instead of re-inserting (which would crash on a
duplicate primary key). It NEVER deletes or modifies existing rows; it only
ADDS new batches with fresh UUIDs, so re-running it is safe (just adds more).

Run from backend/ with DATABASE_URL in env (loaded from .env by default, or
pass --remote <url> to target a specific database explicitly).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import uuid as _uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv


async def main() -> None:
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from credit_engine import recompute_batch_credit
    from db import engine, init_db
    from models import (
        AnnualVerification,
        Batch,
        Kiln,
        MoistureReading,
        Project,
        PortalUser,
        PyrolysisTelemetry,
        RegistryConfig,
        CompositePileSample,
        EndUseApplication,
        YieldMetrics,
    )
    from portal.auth import hash_password

    await init_db()  # idempotent Alembic upgrade — never drops/recreates data

    Session = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    sha = "a" * 64

    CORG_TABLE = {
        "Lantana_camara": 0.60,
        "Wood_chips": 0.55,
        "Agricultural_waste": 0.50,
        "Default": 0.55,
    }

    # --- Get-or-create the fixed reference rows (never re-insert a dup) -----
    async with Session() as s:
        registry = (
            await s.execute(select(RegistryConfig).where(RegistryConfig.config_id == "csi-default"))
        ).scalar_one_or_none()
        if registry is None:
            s.add(
                RegistryConfig(
                    config_id="csi-default",
                    registry_name="Carbon Standards International",
                    methodology_version="CSI-3.2",
                    params_json=json.dumps({"corg_table": CORG_TABLE}),
                )
            )
            print("created RegistryConfig csi-default")
        else:
            print("reusing existing RegistryConfig csi-default")

        project = (
            await s.execute(select(Project).where(Project.project_id == "demo-lantana-01"))
        ).scalar_one_or_none()
        if project is None:
            s.add(
                Project(
                    project_id="demo-lantana-01",
                    name="Demo Biochar Project",
                    registry_config_id="csi-default",
                    allowed_feedstocks=json.dumps(["Lantana_camara"]),
                    client_target=25,
                )
            )
            print("created Project demo-lantana-01")
        else:
            print("reusing existing Project demo-lantana-01")

        demo_user = (
            await s.execute(select(PortalUser).where(PortalUser.email == "demo@terracipher.local"))
        ).scalar_one_or_none()
        if demo_user is None:
            s.add(
                PortalUser(
                    email="demo@terracipher.local",
                    password_hash=hash_password("demo-pass-12345"),
                    role="admin",
                    disabled=False,
                )
            )
            print("created PortalUser demo@terracipher.local")
        else:
            print("reusing existing PortalUser demo@terracipher.local")

        kiln = (
            await s.execute(select(Kiln).where(Kiln.kiln_id == "KILN-DEMO-01"))
        ).scalar_one_or_none()
        if kiln is None:
            s.add(Kiln(kiln_id="KILN-DEMO-01", material="steel", weight_kg=120.0, lifetime_years=10.0))
            print("created Kiln KILN-DEMO-01")
        else:
            print("reusing existing Kiln KILN-DEMO-01")

        # Project-linked batches activate the C9 annual-methane + C10 density
        # gates (see PHASE_1D investigation) — seed a compliant verification
        # for the current year so those two gates don't drown out the
        # intentional variety below. Safe/idempotent: unique on (project_id, year).
        year = now.year
        existing_av = (
            await s.execute(
                select(AnnualVerification).where(
                    AnnualVerification.project_id == "demo-lantana-01",
                    AnnualVerification.year == year,
                )
            )
        ).scalar_one_or_none()
        if existing_av is None:
            s.add(
                AnnualVerification(
                    project_id="demo-lantana-01",
                    year=year,
                    methane_run_count=3,
                    payload_json="{}",
                )
            )
            print(f"created AnnualVerification demo-lantana-01/{year}")
        else:
            print(f"reusing existing AnnualVerification demo-lantana-01/{year}")

        await s.commit()

    # --- helper: one batch through the real pipeline, dated in the past -----
    async def _seed_batch(
        *,
        idx: int,
        months_ago: int,
        day_in_month: int,
        variant: str,  # "issued" or one of the provisional-variant names
    ) -> tuple[str, bool, float, list[str]]:
        buid = str(_uuid.uuid4())
        received_at = (now - timedelta(days=30 * months_ago)).replace(
            day=min(day_in_month, 28), hour=10, minute=0, second=0, microsecond=0
        )
        harvest_ts = received_at - timedelta(days=2)

        # Gentle, deterministic variation so credits differ month to month —
        # never random (reproducible), never so wild it looks fake.
        wet_yield_kg = 85.0 + (idx * 7) % 40
        biomass_kg = 480.0 + (idx * 11) % 60
        moisture = 10.0 + (idx % 6)

        async with Session() as s:
            batch = Batch(
                batch_uuid=buid,
                operation_id=f"op-rich-{idx}-{buid[:8]}",
                feedstock_species="Lantana_camara",
                harvest_timestamp=harvest_ts,
                moisture_percent=moisture,
                harvest_uptime_seconds=100,
                device_id="demo-device",
                latitude=12.9716,
                longitude=77.5946,
                biomass_input_kg=biomass_kg,
                biomass_measurement_method="direct_weigh",
                project_id="demo-lantana-01",
                received_at=received_at,
            )
            if variant != "no_lab":
                batch.lab_h_corg = 0.30
                batch.organic_carbon_pct = 0.60
            s.add(batch)

            if variant != "no_telemetry":
                tel = {
                    "telemetry_uuid": str(_uuid.uuid4()),
                    "batch_uuid": buid,
                    "kiln_type": "open",
                    "kiln_id": "KILN-DEMO-01",
                    "kiln_gross_capacity": 1000.0,
                    "burn_start_timestamp": (harvest_ts + timedelta(hours=1)).isoformat(),
                    "burn_end_timestamp": (harvest_ts + timedelta(hours=3)).isoformat(),
                    "temperature_readings": [630.0 + (idx % 40)] * 60,
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

            if variant != "no_yield":
                s.add(
                    YieldMetrics(
                        yield_uuid=str(_uuid.uuid4()),
                        batch_uuid=buid,
                        payload_json=json.dumps(
                            {
                                "yield_uuid": str(_uuid.uuid4()),
                                "batch_uuid": buid,
                                "wet_yield_weight_kg": wet_yield_kg,
                            }
                        ),
                    )
                )

            if variant != "no_application":
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
                                "delivery_date": (harvest_ts + timedelta(hours=3)).isoformat(),
                                "delivered_amount_kg": 50.0,
                                "buyer_name": "Asha Farmers Co-op",
                            }
                        ),
                    )
                )

            moisture_count = 3 if variant == "few_moisture" else 10
            for i in range(1, moisture_count + 1):
                s.add(
                    MoistureReading(
                        reading_uuid=str(_uuid.uuid4()),
                        batch_uuid=buid,
                        payload_json=json.dumps(
                            {
                                "reading_uuid": str(_uuid.uuid4()),
                                "batch_uuid": buid,
                                "moisture_percent": moisture,
                                "sequence": i,
                                "sha256_hash": sha,
                            }
                        ),
                    )
                )

            if variant != "no_composite":
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

            await s.commit()
            await recompute_batch_credit(s, batch)
            await s.commit()
            await s.refresh(batch)
            reasons = json.loads(batch.provisional_reasons or "[]")
            return buid, batch.provisional, batch.net_credit_t_co2e, reasons

    # 6 months back through this month, 3 batches/month: 2 issued + 1 varied-provisional
    provisional_variants = [
        "no_lab",
        "no_telemetry",
        "no_yield",
        "no_application",
        "few_moisture",
        "no_composite",
    ]
    results = []
    idx = 0
    for months_ago in range(5, -1, -1):
        for slot in range(3):
            variant = "issued" if slot < 2 else provisional_variants[months_ago % len(provisional_variants)]
            day = 5 + slot * 8
            r = await _seed_batch(idx=idx, months_ago=months_ago, day_in_month=day, variant=variant)
            results.append((months_ago, variant, *r))
            idx += 1

    print(f"\nSeeded {len(results)} new batches:")
    for months_ago, variant, buid, provisional, credit, reasons in results:
        print(
            f"  months_ago={months_ago} variant={variant:14s} provisional={provisional!s:5s} "
            f"credit={credit:.4f}  reasons={reasons}  {buid[:8]}"
        )
    print("\nSEED_RICH OK")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a rich, multi-month demo dataset.")
    parser.add_argument("--remote", type=str, help="Optional DATABASE_URL to target explicitly.")
    args = parser.parse_args()

    if args.remote:
        print(f"Seeding target database: {args.remote.split('@')[-1]}")
        os.environ["DATABASE_URL"] = args.remote
    else:
        load_dotenv()
        print("Seeding database from .env DATABASE_URL")

    asyncio.run(main())
