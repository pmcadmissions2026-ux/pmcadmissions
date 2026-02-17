import sys, os
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from config import Config
import requests
key = Config.SUPABASE_SERVICE_KEY or Config.SUPABASE_KEY
url = Config.SUPABASE_URL.rstrip('/') + '/rest/v1/enquiries?select=*'
headers = {
    'apikey': key,
    'Authorization': f'Bearer {key}'
}
print('GET', url)
r = requests.get(url, headers=headers, timeout=15)
print('status', r.status_code)
try:
    data = r.json()
    print('sample rows count:', len(data) if isinstance(data, list) else 'non-list')
    if isinstance(data, list) and len(data):
        print('row keys:', list(data[0].keys()))
    else:
        print('response body:', data)
except Exception:
    print('text', r.text[:2000])
print('headers:', r.headers.get('content-range'))
