import re

with open('backend/tests/test_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix json missing
text = text.replace('async def test_duplicate_idempotency_key_returns_200(client, registered_device):', 'async def test_duplicate_idempotency_key_returns_200(client, registered_device):\n    import json')

# Fix media wrong hash mixup
text = text.replace('"X-Declared-SHA256": wrong_hash,', '"X-Declared-SHA256": expected_hash,')
text = text.replace('wrong_hash = hashlib.sha256(b"different_content").hexdigest()', 'expected_hash = hashlib.sha256(b"different_content").hexdigest()')

# Also we need to inject telemetry
telemetry_injector = '''
    dev_id = registered_device['device_id']
    tel_payload = {"telemetry_uuid": "tel-"+uuid4().hex, "batch_uuid": payload["batch_uuid"], "timestamp": "2026-01-15T08:30:00Z", "pyrolysis_temperature": 600.0}
    tel_sig = sign_request(dev_id, registered_device['b64_key'], 'POST', '/api/v1/telemetry', 'op-tel', tel_payload)
    await client.post('/api/v1/telemetry', content=json.dumps(tel_payload).encode('utf-8'), headers={'X-Idempotency-Key': 'op-tel', 'X-Device-Id': dev_id, 'X-HMAC-Signature': tel_sig})
    
    response = await client.post(
'''

# We only want to inject this before the main `/api/v1/batches` POST.
def replace_batch_post(m):
    return m.group(0).replace('    response = await client.post(', telemetry_injector)

text = re.sub(r'    response = await client\.post\(\s*"/api/v1/batches"', replace_batch_post, text)
text = re.sub(r'    response1 = await client\.post\(\s*"/api/v1/batches"', replace_batch_post.replace('response', 'response1'), text)

with open('backend/tests/test_api.py', 'w', encoding='utf-8') as f:
    f.write(text)
