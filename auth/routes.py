from flask import Blueprint, render_template, request, session, redirect, url_for, flash, current_app
from database.models import UserModel
from database.supabase_config import db
from datetime import datetime
import os
from flask import jsonify
from config import Config

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login route"""
    # Protect against stale sessions stored in cookies (e.g., after DB user deleted)
    if 'user_id' in session:
        try:
            user_check = UserModel.get_user_by_id(session['user_id'])
            if not user_check:
                session.clear()
        except Exception:
            session.clear()

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role_selection = request.form.get('role')
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        # Verify user credentials
        user = UserModel.verify_login(email, password)
        
        if user:
            # Get user role
            role = UserModel.get_user_role(user['user_id'])
            
            if role:
                # Create session
                session['user_id'] = user['user_id']
                session['user_email'] = user['email']
                session['user_name'] = f"{user.get('first_name', '')} {user.get('last_name', '')}"
                session['user_role'] = role['role_name']
                session['employee_id'] = user['employee_id']
                
                # Update last login
                UserModel.update_last_login(user['user_id'])
                
                # Log session
                db.insert('session_log', {
                    'user_id': user['user_id'],
                    'session_start': datetime.now().isoformat(),
                    'ip_address': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent')
                })
                
                # Redirect based on role
                if role['role_name'] in ['super_admin', 'admin']:
                    return redirect(url_for('admin.dashboard'))
                else:
                    return redirect(url_for('student.step1'))
            else:
                flash('User role not found', 'error')
        else:
            flash('Invalid email or password', 'error')
        
        return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')


# Temporary debug endpoint (disabled by default). Enable by setting
# `ENABLE_DEBUG_ENDPOINT=1` in the environment. Returns whether the
# provided email exists in the `users` table. Use only for debugging.
@auth_bp.route('/debug/user_exists')
def debug_user_exists():
    if os.getenv('ENABLE_DEBUG_ENDPOINT') != '1' and not current_app.debug:
        return jsonify({'error': 'disabled'}), 403

    email = request.args.get('email')
    if not email:
        return jsonify({'error': 'email required'}), 400

    user = UserModel.get_user_by_email(email)
    exists = bool(user)
    return jsonify({'email': email, 'exists': exists}), 200


@auth_bp.route('/debug/env')
def debug_env():
    if os.getenv('ENABLE_DEBUG_ENDPOINT') != '1' and not current_app.debug:
        return jsonify({'error': 'disabled'}), 403

    # Determine which Supabase key is present (service vs anon) and show only length
    supabase_url = os.getenv('SUPABASE_URL') or Config.SUPABASE_URL
    service_key = os.getenv('SUPABASE_SERVICE_KEY') or Config.SUPABASE_SERVICE_KEY
    anon_key = os.getenv('SUPABASE_KEY') or Config.SUPABASE_KEY

    url_host = None
    if supabase_url:
        try:
            from urllib.parse import urlparse
            url_host = urlparse(supabase_url).netloc
        except Exception:
            url_host = supabase_url

    client_key_type = 'SERVICE' if service_key else ('ANON' if anon_key else 'NONE')
    key_len = len(service_key) if service_key else (len(anon_key) if anon_key else 0)

    # Use db.count for a lightweight permission check (uses the Supabase client)
    users_count = None
    try:
        users_count = db.count('users')
    except Exception as e:
        users_count = f'error: {str(e)}'

    # Additional direct REST check (bypasses client library) to verify
    # whether the key can read the `users` table via Supabase REST endpoint.
    rest_status = None
    rest_count_sample = None
    rest_error = None
    try:
        import requests
        key_for_rest = service_key or anon_key
        if supabase_url and key_for_rest:
            rest_headers = {
                'apikey': key_for_rest,
                'Authorization': f'Bearer {key_for_rest}',
                'Prefer': 'count=exact'
            }
            rest_url = f"{supabase_url.rstrip('/')}/rest/v1/users"
            r = requests.get(rest_url, headers=rest_headers, params={'select':'*', 'limit':1}, timeout=10)
            rest_status = r.status_code
            try:
                rest_json = r.json()
                rest_count_sample = len(rest_json) if isinstance(rest_json, list) else None
            except Exception:
                rest_count_sample = None
        else:
            rest_error = 'missing supabase_url or key'
    except Exception as e:
        rest_error = str(e)

    return jsonify({
        'supabase_url_host': url_host,
        'client_key_type': client_key_type,
        'supabase_key_length': key_len,
        'users_table_count_sample': users_count,
        'rest_check_status': rest_status,
        'rest_check_count_sample': rest_count_sample,
        'rest_check_error': rest_error
    }), 200

@auth_bp.route('/logout')
def logout():
    """User logout route"""
    if 'user_id' in session:
        # Update session end time
        sessions = db.select('session_log', filters={'user_id': session['user_id']})
        if sessions:
            latest_session = max(sessions, key=lambda x: x['session_start'])
            db.update('session_log', 
                     {'session_end': datetime.now().isoformat()},
                     {'session_id': latest_session['session_id']})
    
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('auth.login'))

@auth_bp.route('/unauthorized')
def unauthorized():
    """Unauthorized access page"""
    return render_template('auth/unauthorized.html'), 403

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route (For admins only)"""
    if 'user_role' not in session or session['user_role'] != 'super_admin':
        return redirect(url_for('auth.unauthorized'))
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        role_id = request.form.get('role_id')
        
        # Validate inputs
        if not all([employee_id, email, password, first_name, role_id]):
            flash('All fields are required', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user exists
        existing_user = UserModel.get_user_by_email(email)
        if existing_user:
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        # Create user
        try:
            UserModel.create_user(employee_id, email, password, first_name, 
                                last_name, role_id, phone)
            flash(f'User {email} registered successfully', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            flash(f'Error registering user: {str(e)}', 'error')
            return redirect(url_for('auth.register'))
    
    # Get roles for dropdown
    roles = db.select('roles')
    return render_template('auth/register.html', roles=roles)
