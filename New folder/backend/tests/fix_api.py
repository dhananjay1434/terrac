import re

with open('backend/tests/test_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix response1/response2
text = text.replace('        headers={"X-Idempotency-Key": operation_id, "X-Device-Id": dev_id, "X-HMAC-Signature": sig},\n    )\n    assert response1.status_code == 201', '        headers={"X-Idempotency-Key": operation_id, "X-Device-Id": dev_id, "X-HMAC-Signature": sig},\n    )\n    response1 = response\n    assert response1.status_code == 201')
text = text.replace('        headers={"X-Idempotency-Key": operation_id, "X-Device-Id": dev_id, "X-HMAC-Signature": sig},\n    )\n    assert response2.status_code == 200', '        headers={"X-Idempotency-Key": operation_id, "X-Device-Id": dev_id, "X-HMAC-Signature": sig},\n    )\n    response2 = response\n    assert response2.status_code == 200')

# Fix media wrong hash
text = text.replace('"X-Declared-SHA256": expected_hash,', '"X-Declared-SHA256": wrong_hash,', 1)

# Fix response1 for media
text = text.replace('        headers={\n            "X-Idempotency-Key": operation_id,\n            "X-Declared-SHA256": expected_hash,\n            "X-Device-Id": dev_id,\n            "X-HMAC-Signature": sig,\n        },\n    )\n    assert response1.status_code == 200', '        headers={\n            "X-Idempotency-Key": operation_id,\n            "X-Declared-SHA256": expected_hash,\n            "X-Device-Id": dev_id,\n            "X-HMAC-Signature": sig,\n        },\n    )\n    response1 = response\n    assert response1.status_code == 200')

text = text.replace('        headers={\n            "X-Idempotency-Key": operation_id,\n            "X-Declared-SHA256": expected_hash,\n            "X-Device-Id": dev_id,\n            "X-HMAC-Signature": sig,\n        },\n    )\n    assert response2.status_code == 200', '        headers={\n            "X-Idempotency-Key": operation_id,\n            "X-Declared-SHA256": expected_hash,\n            "X-Device-Id": dev_id,\n            "X-HMAC-Signature": sig,\n        },\n    )\n    response2 = response\n    assert response2.status_code == 200')

# Fix test_extra_field
text = text.replace('async def test_extra_field_ignored_returns_201(client):', 'async def test_extra_field_ignored_returns_201(client, registered_device):')

with open('backend/tests/test_api.py', 'w', encoding='utf-8') as f:
    f.write(text)
