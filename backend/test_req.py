import urllib.request, json, urllib.error
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/register', method='POST', headers={'Content-Type': 'application/json', 'X-Enrollment-Token': 'dev-token'}, data=json.dumps({'device_id':'test-device','hmac_key':'test-key-test-key-test-key-test-key-test-key-test-key'}).encode('utf-8'))
try:
  urllib.request.urlopen(req)
except urllib.error.HTTPError as e:
  print(e.read().decode())
