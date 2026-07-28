import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from db import DATABASE_URL
from models import Batch, TelemetryPoint

async def main():
    print("Generating 100k synthetic batches (without credit pipeline)...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with SessionLocal() as session:
        # Check if we already seeded
        res = await session.execute(text("SELECT COUNT(*) FROM batches WHERE device_id = 'synth-device'"))
        count = res.scalar()
        if count >= 100000:
            print(f"Already seeded {count} synth batches.")
        else:
            # We use raw SQL for speed
            print("Seeding batches using raw SQL...")
            await session.execute(text("DELETE FROM batches WHERE device_id = 'synth-device'"))
            await session.commit()
            
            # Batch size for inserts
            batch_size = 5000
            for i in range(0, 100000, batch_size):
                print(f"Inserting {i} to {i+batch_size} batches...")
                now = datetime.now(timezone.utc)
                values = []
                for j in range(batch_size):
                    bid = f"synth-batch-{i+j:06d}"
                    site_id = f"site-{j%10}"
                    network_id = f"net-{j%2}"
                    yield_kg = 50.0 + (j%100)
                    dt_str = (now - timedelta(days=j%365)).strftime("%Y-%m-%d %H:%M:%S")
                    values.append(
                        f"('{bid}', 'synth-device', '{dt_str}', 'biochar', 'issued', {yield_kg}, 'bamboo', '{site_id}', '{network_id}')"
                    )
                
                query = f"""
                    INSERT INTO batches (
                        batch_uuid, device_id, harvest_timestamp, kind, status, 
                        biomass_input_kg, feedstock_species, site_id, network_id
                    ) VALUES {','.join(values)}
                """
                await session.execute(text(query))
                await session.commit()

            print("Batches seeded. Now seeding some telemetry points for the first 100 batches to test point queries...")
            await session.execute(text("DELETE FROM telemetry_points WHERE batch_uuid LIKE 'synth-batch-%'"))
            await session.commit()
            
            for i in range(100):
                bid = f"synth-batch-{i:06d}"
                tel_values = []
                base_time = datetime.now(timezone.utc)
                for t in range(300):
                    dt_str = (base_time + timedelta(seconds=t*10)).strftime("%Y-%m-%d %H:%M:%S")
                    for chan in ["T1", "T2", "T3", "T4"]:
                        tel_values.append(f"('{bid}', '{dt_str}', '{chan}', {400 + t})")
                query = f"""
                    INSERT INTO telemetry_points (batch_uuid, ts, channel, value)
                    VALUES {','.join(tel_values)}
                    ON CONFLICT DO NOTHING
                """
                await session.execute(text(query))
                await session.commit()
            print("Telemetry points seeded.")

        print("Testing telemetry bridge read performance via EXPLAIN ANALYZE...")
        bid = "synth-batch-000001"
        explain_q = f"""
            EXPLAIN ANALYZE
            SELECT ts, value FROM telemetry_points 
            WHERE batch_uuid = '{bid}' 
            AND channel IN ('T1', 'T2', 'T3') 
            ORDER BY ts
        """
        res = await session.execute(text(explain_q))
        print("\n".join([row[0] for row in res.all()]))
        
        print("\nTesting ledger batches read performance via EXPLAIN ANALYZE...")
        explain_ledger = """
            EXPLAIN ANALYZE
            SELECT id FROM batches 
            WHERE site_id = 'site-1' 
            AND network_id = 'net-1'
        """
        res = await session.execute(text(explain_ledger))
        print("\n".join([row[0] for row in res.all()]))

if __name__ == "__main__":
    asyncio.run(main())
