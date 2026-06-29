import json
import hashlib
import hmac
import base64

def sign_request(device_id: str, b64_key: str, method: str, path: str, op_id: str, payload: dict) -> str:
    raw_body = json.dumps(payload).encode("utf-8")
    canonical = "\n".join([method, path, op_id, hashlib.sha256(raw_body).hexdigest(), device_id]).encode("utf-8")
    
    # We pad the b64 key and decode it
    padding = '=' * (4 - (len(b64_key) % 4))
    secret = base64.urlsafe_b64decode(b64_key + padding)
    
    return hmac.new(secret, canonical, hashlib.sha256).hexdigest()
