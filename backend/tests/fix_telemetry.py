import re

with open('backend/tests/test_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

helper = '''
async def inject_telemetry(client, dev_id, b64_key, batch_uuid):
    from uuid import uuid4
    import json
    from tests.remediation.crypto_utils import sign_request
    tel_payload = {"telemetry_uuid": "tel-"+uuid4().hex, "batch_uuid": batch_uuid, "timestamp": "2026-01-15T08:30:00Z", "pyrolysis_temperature": 600.0}
    tel_sig = sign_request(dev_id, b64_key, 'POST', '/api/v1/telemetry', 'op-tel', tel_payload)
    await client.post('/api/v1/telemetry', content=json.dumps(tel_payload).encode('utf-8'), headers={'X-Idempotency-Key': 'op-tel', 'X-Device-Id': dev_id, 'X-HMAC-Signature': tel_sig})

'''

if 'async def inject_telemetry' not in text:
    text = text.replace('import json\nfrom uuid import uuid4', helper + 'import json\nfrom uuid import uuid4')

def inject_call(m):
    return f"    await inject_telemetry(client, registered_device['device_id'], registered_device['b64_key'], payload['batch_uuid'])\n{m.group(0)}"

text = re.sub(r'    response = await client\.post\(\s*"/api/v1/batches"', inject_call, text)
text = re.sub(r'    response1 = await client\.post\(\s*"/api/v1/batches"', inject_call, text)

with open('backend/tests/test_api.py', 'w', encoding='utf-8') as f:
    f.write(text)
