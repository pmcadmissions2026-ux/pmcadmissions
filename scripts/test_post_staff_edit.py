import sys, os
proj_root = os.path.dirname(os.path.dirname(__file__))
if proj_root not in sys.path:
    sys.path.insert(0, proj_root)

from app import app
from database.supabase_config import db
import json

# Ensure debug logging prints
app.testing = True

with app.test_client() as client:
    # Set session to simulate authenticated super_admin
    with client.session_transaction() as sess:
        sess['user_id'] = 7
        sess['user_role'] = 'super_admin'
        sess['user_name'] = 'TestLocal'

    form = {
        'first_name': 'TCFirst',
        'last_name': 'TCLast',
        'email': 'testlocal+7@example.com',
        'phone': '',
        'role_id': '2',
        'is_active': 'on',
        # Multiple modules entries
        'modules': ['dashboard', 'enquiries']
    }

    print('Posting to /admin/staff/7/edit ...')
    resp = client.post('/admin/staff/7/edit', data=form, follow_redirects=True)
    print('Response status:', resp.status_code)
    print('Response data snippet:', resp.data[:1000])

    # Check DB value
    rows = db.select('users', filters={'user_id': 7})
    print('DB select for user 7:', rows)
