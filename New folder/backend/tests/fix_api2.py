with open('backend/tests/test_api.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('json=payload,', 'content=json.dumps(payload).encode("utf-8"),')

with open('backend/tests/test_api.py', 'w', encoding='utf-8') as f:
    f.write(text)
