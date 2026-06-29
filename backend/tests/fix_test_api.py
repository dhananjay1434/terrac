import re

with open('backend/tests/test_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('async def test_valid_payload_returns_201(client):', 'async def test_valid_payload_returns_201(client, registered_device):')
text = text.replace('async def test_duplicate_idempotency_key_returns_200(client):', 'async def test_duplicate_idempotency_key_returns_200(client, registered_device):')
text = text.replace('async def test_missing_sha256_hash_returns_422(client):', 'async def test_missing_sha256_hash_returns_422(client, registered_device):')
text = text.replace('async def test_invalid_moisture_percent_returns_422(client):', 'async def test_invalid_moisture_percent_returns_422(client, registered_device):')

text = text.replace('from models import Base\n', 'from models import Base\nfrom tests.remediation.crypto_utils import sign_request\n\n')

def replace_batch_post(m):
    return '''    import json
    dev_id = registered_device['device_id']
    sig = sign_request(dev_id, registered_device['b64_key'], 'POST', '/api/v1/batches', operation_id, payload)
    
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Idempotency-Key": operation_id, "X-Device-Id": dev_id, "X-HMAC-Signature": sig},
    )'''

text = re.sub(r'    response = await client\.post\(\s*\"/api/v1/batches\",\s*json=payload,\s*headers={\"X-Idempotency-Key\": operation_id},\s*\)', replace_batch_post, text)

def replace_batch_post_no_idem(m):
    return '''    import json
    dev_id = registered_device['device_id']
    sig = sign_request(dev_id, registered_device['b64_key'], 'POST', '/api/v1/batches', '', payload)
    
    response = await client.post(
        "/api/v1/batches",
        json=payload,
        headers={"X-Device-Id": dev_id, "X-HMAC-Signature": sig},
    )'''
text = text.replace('async def test_missing_idempotency_key_returns_422(client):', 'async def test_missing_idempotency_key_returns_422(client, registered_device):')
text = re.sub(r'    response = await client\.post\(\s*\"/api/v1/batches\",\s*json=payload,\s*\)', replace_batch_post_no_idem, text)

# Media upload tests
text = text.replace('async def test_media_upload_correct_hash_returns_200(client):', 'async def test_media_upload_correct_hash_returns_200(client, registered_device):')
text = text.replace('async def test_media_upload_wrong_hash_returns_422(client):', 'async def test_media_upload_wrong_hash_returns_422(client, registered_device):')
text = text.replace('async def test_media_duplicate_idempotency_key(client):', 'async def test_media_duplicate_idempotency_key(client, registered_device):')

def replace_media_post(m):
    return '''    import json
    dev_id = registered_device['device_id']
    sig = sign_request(dev_id, registered_device['b64_key'], 'POST', '/api/v1/media', operation_id, None)
    
    response = await client.post(
        "/api/v1/media",
        files=files,
        headers={
            "X-Idempotency-Key": operation_id,
            "X-Declared-SHA256": expected_hash,
            "X-Device-Id": dev_id,
            "X-HMAC-Signature": sig,
        },
    )'''
# Note: Since the media post requests have variations (like files=files1 vs files=files2), we can just replace them using a more generic regex
text = re.sub(r'    response = await client\.post\(\s*\"/api/v1/media\",\s*files=files,\s*headers=\{.*?\},\s*\)', replace_media_post, text, flags=re.DOTALL)

def replace_media_post1(m):
    return replace_media_post(m).replace('files=files', 'files=files1')
def replace_media_post2(m):
    return replace_media_post(m).replace('files=files', 'files=files2')

text = re.sub(r'    response1 = await client\.post\(\s*\"/api/v1/media\",\s*files=files1,\s*headers=\{.*?\},\s*\)', replace_media_post1, text, flags=re.DOTALL)
text = re.sub(r'    response2 = await client\.post\(\s*\"/api/v1/media\",\s*files=files2,\s*headers=\{.*?\},\s*\)', replace_media_post2, text, flags=re.DOTALL)


with open('backend/tests/test_api.py', 'w', encoding='utf-8') as f:
    f.write(text)

