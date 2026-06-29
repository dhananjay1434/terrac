import asyncio
from dotenv import load_dotenv
load_dotenv()
from db import SessionLocal
from models import EnrollmentToken, DeviceKey
from sqlalchemy import select, update

async def run():
    async with SessionLocal() as s:
        # Reset token
        await s.execute(update(EnrollmentToken).where(EnrollmentToken.token == 'dev-token').values(used_at=None))
        
        # Check token
        r = await s.execute(select(EnrollmentToken.token, EnrollmentToken.used_at))
        print("Tokens:", r.fetchall())
        
        # Check devices
        r2 = await s.execute(select(DeviceKey.device_id, DeviceKey.hmac_key))
        print("Devices:", r2.fetchall())
        
        await s.commit()

asyncio.run(run())
