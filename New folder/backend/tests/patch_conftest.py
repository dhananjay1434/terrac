import re

with open('backend/tests/conftest.py', 'r', encoding='utf-8') as f:
    text = f.read()

wrapper = '''
class SignedAsyncClient:
    def __init__(self, async_client, session_factory):
        self.ac = async_client
        self.session_factory = session_factory
    
    def __getattr__(self, name):
        return getattr(self.ac, name)

    async def post(self, url, **kwargs):
        import json, base64
        from tests.remediation.crypto_utils import sign_request
        from uuid import uuid4
        
        b64_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode('utf-8')
        dev_id = "test-device-reg"
        
        if url == "/api/v1/batches":
            payload = kwargs.get("json") or (json.loads(kwargs.get("content").decode('utf-8')) if kwargs.get("content") else None)
            if payload and "batch_uuid" in payload:
                # Inject a telemetry log for this batch_uuid
                tel_payload = {"telemetry_uuid": "tel-"+uuid4().hex, "batch_uuid": payload["batch_uuid"], "timestamp": "2026-01-15T08:30:00Z", "pyrolysis_temperature": 600.0}
                tel_sig = sign_request(dev_id, b64_key, "POST", "/api/v1/telemetry", "op-tel", tel_payload)
                await self.ac.post("/api/v1/telemetry", content=json.dumps(tel_payload).encode('utf-8'), headers={"X-Idempotency-Key": "op-tel", "X-Device-Id": dev_id, "X-HMAC-Signature": tel_sig})
                
        # Re-encode json to content for accurate signing if it's there
        payload = kwargs.get("json")
        if payload is not None:
            kwargs["content"] = json.dumps(payload).encode('utf-8')
            del kwargs["json"]

        headers = kwargs.get("headers", {})
        
        # Don't overwrite if it's already provided (e.g. for testing failures)
        if "X-HMAC-Signature" not in headers and "X-Device-Id" not in headers:
            headers["X-Device-Id"] = dev_id
            content = kwargs.get("content")
            payload_dict = json.loads(content.decode('utf-8')) if content else None
            op_id = headers.get("X-Idempotency-Key", "")
            sig = sign_request(dev_id, b64_key, "POST", url, op_id, payload_dict)
            headers["X-HMAC-Signature"] = sig
            
        kwargs["headers"] = headers
        return await self.ac.post(url, **kwargs)

@pytest_asyncio.fixture(scope="function")
async def client(session_factory):
    from server import app, get_session
    import base64, json
    from models import EnrollmentToken
    from httpx import ASGITransport

    async def override_session():
        async with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    
    # Pre-register the device
    async with session_factory() as session:
        session.add(EnrollmentToken(token="test-credit"))
        await session.commit()
        
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        b64_key = base64.urlsafe_b64encode(b"12345678901234567890123456789012").decode('utf-8')
        payload = {"device_id": "test-device-reg", "hmac_key": b64_key}
        await ac.post("/api/v1/register", content=json.dumps(payload).encode('utf-8'), headers={"X-Enrollment-Token": "test-credit", "X-HMAC-Signature": "dummy"})
        
        signed_ac = SignedAsyncClient(ac, session_factory)
        yield signed_ac
        
    app.dependency_overrides.clear()
'''

if 'class SignedAsyncClient:' not in text:
    text = re.sub(r'@pytest_asyncio\.fixture\(scope="function"\)\nasync def client\(session_factory\):.*(?=\n@pytest_asyncio\.fixture)', wrapper, text, flags=re.DOTALL)
    
    with open('backend/tests/conftest.py', 'w', encoding='utf-8') as f:
        f.write(text)
