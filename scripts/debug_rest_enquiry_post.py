import sys, os
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from config import Config
import requests, json

url = Config.SUPABASE_URL.rstrip('/') + '/rest/v1/enquiries'
key = Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY
print('REST URL:', url)
print('Key len:', len(key) if key else None)
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}',
    'Content-Type': 'application/json',
    'Prefer': 'return=representation'
}
body = {
    'student_id': None,
    'full_name': 'REST Test',
    'phone': '9999999999',
    'email': 'resttest@example.com',
    'query_subject': 'Subject',
    'query_description': 'desc'
}
try:
    r = requests.post(url, headers=headers, json=body, timeout=15)
    print('status', r.status_code)
    try:
        print('json', r.json())
    except Exception:
        print('text', r.text[:1000])
    print('headers content-range:', r.headers.get('content-range'))
except Exception as e:
    print('error', e)
