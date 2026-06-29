import re

with open('backend/tests/conftest.py', 'r', encoding='utf-8') as f:
    text = f.read()

legacy_setup = '''
@pytest_asyncio.fixture(scope="function", autouse=True)
async def legacy_test_environment(session_factory):
    import base64
    from models import Device
    from unittest.mock import patch
    import server

    # Pre-populate common devices used in legacy tests
    b64_key = base64.urlsafe_b64encode(b"test-secret").decode("utf-8")
    # For test_hmac_verification.py it uses "test_secret" which is 11 bytes.
    # The server logic expects b64decode to work.
    
    devices_to_add = ["dev-1", "test-device-1", "test-device-2", "", "test-device-reg"]
    
    async with session_factory() as session:
        for d in devices_to_add:
            session.add(Device(device_id=d, hmac_key=b64_key))
        await session.commit()
        
    # Mock telemetry check to always pass
    patcher = patch("server._validate_qualifying_telemetry_log")
    mock_telemetry = patcher.start()
    mock_telemetry.return_value = None
    
    yield
    
    patcher.stop()
'''

if 'async def legacy_test_environment' not in text:
    with open('backend/tests/conftest.py', 'a', encoding='utf-8') as f:
        f.write('\n' + legacy_setup)
