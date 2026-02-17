import json
import datetime
import sys, os
# Ensure project root is on sys.path when running this script directly
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)
from database.supabase_config import db

update_data = {
    'first_name': 'TestLocal',
    'last_name': 'UserLocal',
    'email': 'testlocal+7@example.com',
    'phone': None,
    'role_id': 2,
    'is_active': True,
    'assigned_modules': json.dumps(['dashboard', 'enquiries']),
    'updated_at': datetime.datetime.utcnow().isoformat()
}

print('Calling db.update with payload:')
print(update_data)

try:
    res = db.update('users', update_data, {'user_id': 7})
    print('Result:', res)
except Exception as e:
    import traceback
    print('Exception calling db.update:', e)
    traceback.print_exc()
