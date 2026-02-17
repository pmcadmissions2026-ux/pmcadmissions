from app import app
from database.supabase_config import db
import json

with app.test_client() as client:
    # Create a test admin user
    user = {
        'employee_id': 'T001',
        'email': 'test.admin@example.com',
        'password': 'secret',
        'first_name': 'Test',
        'last_name': 'Admin',
        'role_id': 2,  # assume 2 -> admin
        'is_active': True,
        'created_at': None
    }
    res = db.insert('users', user)
    if not res:
        # Possibly user exists; try to look up by email or employee_id
        existing = db.select('users', filters={'email': user['email']})
        if not existing:
            existing = db.select('users', filters={'employee_id': user['employee_id']})
        if not existing:
            print('Failed to create or find test user:', res)
            raise SystemExit(1)
        res = existing
    # Determine returned primary key field (could be 'id' or 'user_id')
    row = res[0]
    pk_field = None
    for k in ('user_id', 'id'):
        if k in row:
            pk_field = k
            break
    if not pk_field:
        # fallback to first key that endswith 'id'
        for k in row.keys():
            if k.endswith('id'):
                pk_field = k
                break
    if not pk_field:
        print('Unable to determine user primary key from insert result:', row)
        raise SystemExit(1)

    user_id = row.get(pk_field)
    # Assign modules to user (store as JSON string in assigned_modules)
    assigned = ['enquiries', 'applications']
    db.update('users', {'assigned_modules': json.dumps(assigned)}, {pk_field: user_id})

    # Verify assigned modules updated
    refreshed = db.select('users', filters={pk_field: user_id})
    print('Refreshed user row:', refreshed)

    # Set session values
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['user_role'] = 'admin'
        sess['user_name'] = 'Test Admin'

    # Prepare form data
    form = {
        'full_name': 'Auto Test Student',
        'plus2_register_number': '26000123',
        'whatsapp_number': '9999998888',
        'email': 'autotest.student@example.com',
        'father_name': 'Father Name',
        'mother_name': 'Mother Name',
        'date_of_birth': '2004-01-01',
        'gender': 'Male',
        'aadhar_number': '123412341234',
        'tenth_school_name': 'Test HS',
        'tenth_marks': '450',
        'tenth_total_marks': '500',
        'tenth_year': '2022',
        'plus2_school_name': 'Test +2',
        'plus2_marks': '470',
        'plus2_total_marks': '500',
        'plus2_year': '2024',
        'maths_marks': '95',
        'physics_marks': '90',
        'chemistry_marks': '92',
        'board': 'State Board',
        'general_quota': 'OC'
    }

    print('Posting to /admin/enquiries/new...')
    r = client.post('/admin/enquiries/new', data=form, follow_redirects=False)
    print('Status code:', r.status_code)
    if 'Location' in r.headers:
        loc = r.headers.get('Location')
        print('Redirect to:', loc)
        follow = client.get(loc)
        print('Follow status:', follow.status_code)
        print('Followed content excerpt:', follow.get_data(as_text=True)[:600])
    data = r.get_data(as_text=True)
    print('Response length:', len(data))
    # Check DB for the created student and enquiry
    created_students = db.select('students', filters={'email': form['email']})
    print('Students with email:', created_students)
    created_enqs = db.select('enquiries', filters={'email': form['email']})
    print('Enquiries with email:', created_enqs)
    # Print short excerpt around flash messages
    start = data.find('flash')
    if start != -1:
        print(data[start:start+500])
    else:
        print(data[:1000])
