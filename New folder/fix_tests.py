import os
import re

for filepath in ['backend/tests/remediation/test_mock_gps_server_side.py', 'backend/tests/remediation/test_temperature_log_verification.py']:
    with open(filepath, 'r', encoding='utf-8') as f:
        text = f.read()

    # Replace json=payload, headers=headers with content=json.dumps(payload).encode('utf-8'), headers=headers
    text = re.sub(r'json=([a-zA-Z0-9_]+),\s*headers=', r'content=json.dumps(\1).encode("utf-8"), headers=', text)
    
    # Replace test_db_session
    text = text.replace('test_db_session, ', '')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(text)
