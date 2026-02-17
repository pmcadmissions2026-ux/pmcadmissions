import os, sys, json
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from config import Config
import requests
key = Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY
url = Config.SUPABASE_URL.rstrip('/') + '/rest/v1/enquiries'
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}
# Sample payload — adjust fields as your schema expects
payload = {
    'student_name': 'Test User',
    'whatsapp_number': '1234567890',
    'email': 'test.user@example.com',
    'subject': 'REST Insert Test',
    'preferred_course': 'Undeclared',
    'source': 'debug-script'
}
print('POST', url)
print('headers apikey masked:', '***' + (key[-6:] if key else ''))
try:
    r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    print('status', r.status_code)
    try:
        print('json:', r.json())
    except Exception:
        print('text:', r.text)
except Exception as e:
    print('request error:', repr(e))
