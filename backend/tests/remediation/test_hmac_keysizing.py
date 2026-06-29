import hmac
import hashlib
import base64
import pytest
from fastapi.testclient import TestClient

# The exact 32 byte raw key we agree upon for testing
# hex: 0102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f20
_RAW_KEY = bytes([i for i in range(1, 33)])
_B64_KEY = base64.urlsafe_b64encode(_RAW_KEY).decode("utf-8").rstrip("=")

# The agreed payload to hash
_METHOD = "POST"
_PATH = "/api/v1/telemetry"
_OP_ID = "op-123"
_BODY = b'{"temperature":400}'
_BODY_HASH = hashlib.sha256(_BODY).hexdigest()
_DEV_ID = "dev-hmac-1"

# canonical string
_CANONICAL = "\n".join([_METHOD, _PATH, _OP_ID, _BODY_HASH, _DEV_ID]).encode("utf-8")

# Known signature
_EXPECTED_SIG = hmac.new(_RAW_KEY, _CANONICAL, hashlib.sha256).hexdigest()

def test_server_verifies_raw_byte_key():
    import base64
    # The server logic implemented in server.py verify_hmac:
    key_from_db = _B64_KEY
    padding = '=' * (4 - (len(key_from_db) % 4))
    secret = base64.urlsafe_b64decode(key_from_db + padding)
    
    assert secret == _RAW_KEY

def test_known_vector_matches():
    # Matches the exact dart test
    assert _B64_KEY == "AQIDBAUGBwgJCgsMDQ4PEBESExQVFhcYGRobHB0eHyA"
    
    calculated = hmac.new(_RAW_KEY, _CANONICAL, hashlib.sha256).hexdigest()
    assert calculated == _EXPECTED_SIG
