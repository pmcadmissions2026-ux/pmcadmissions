from flask import Blueprint, render_template, jsonify, current_app, session, make_response
from database.supabase_config import db
from config import Config
import os
import requests
import traceback
import sys

test_bp = Blueprint('test', __name__, url_prefix='/test')


@test_bp.route('/')
def index():
    supabase_url = os.getenv('SUPABASE_URL') or Config.SUPABASE_URL
    anon_key = os.getenv('SUPABASE_KEY') or Config.SUPABASE_KEY
    return render_template('test_supabase.html', supabase_url=supabase_url, anon_key=anon_key)


@test_bp.route('/server_fetch')
def server_fetch():
    supabase_url = os.getenv('SUPABASE_URL') or Config.SUPABASE_URL
    service_key = os.getenv('SUPABASE_SERVICE_KEY') or Config.SUPABASE_SERVICE_KEY
    result = {'count': None, 'rest': None}
    try:
        result['count'] = db.count('users')
    except Exception as e:
        result['count'] = f'error: {str(e)}'

    if supabase_url and service_key:
        try:
            headers = {
                'apikey': service_key,
                'Authorization': f'Bearer {service_key}',
                'Prefer': 'count=exact'
            }
            r = requests.get(f"{supabase_url.rstrip('/')}/rest/v1/users?select=*&limit=5", headers=headers, timeout=10)
            rest_info = {'status': r.status_code}
            try:
                j = r.json()
                rest_info['count_sample'] = len(j) if isinstance(j, list) else None
            except Exception:
                rest_info['count_sample'] = None
            result['rest'] = rest_info
        except Exception as e:
            result['rest'] = {'error': str(e)}

    return jsonify(result)


@test_bp.route('/diagnostics')
def diagnostics():
    """Run a set of server-side diagnostic checks and return masked results.

    This endpoint intentionally provides detailed error information (stack
    traces) to help debug deployment-only failures. Do NOT enable in
    production; remove after debugging.
    """
    out = {
        'supabase_url': None,
        'client_key_type': None,
        'supabase_key_length': 0,
        'service_key_masked': None,
        'anon_key_masked': None,
        'client_create': None,
        'client_exception': None,
        'db_count': None,
        'db_count_exception': None,
        'rest_status': None,
        'rest_exception': None,
        'timestamp': None
    }

    supabase_url = os.getenv('SUPABASE_URL') or Config.SUPABASE_URL
    service_key = os.getenv('SUPABASE_SERVICE_KEY') or Config.SUPABASE_SERVICE_KEY
    anon_key = os.getenv('SUPABASE_KEY') or Config.SUPABASE_KEY

    out['supabase_url'] = supabase_url
    out['client_key_type'] = 'SERVICE' if service_key else ('ANON' if anon_key else 'NONE')
    out['supabase_key_length'] = len(service_key) if service_key else (len(anon_key) if anon_key else 0)

    def mask(k):
        if not k:
            return None
        k = k.strip()
        if len(k) <= 8:
            return k[0:1] + '...' + k[-1:]
        return f"{k[:4]}...{k[-4:]}"

    out['service_key_masked'] = mask(service_key)
    out['anon_key_masked'] = mask(anon_key)

    # Attempt to create client via db.client
    try:
        client = db.client
        out['client_create'] = 'ok'
    except Exception as e:
        out['client_create'] = 'failed'
        out['client_exception'] = traceback.format_exc()

    # Try db.count('users')
    try:
        cnt = db.count('users')
        out['db_count'] = cnt
    except Exception:
        out['db_count_exception'] = traceback.format_exc()

    # Direct REST call using service_key if present otherwise anon
    try:
        key_for_rest = service_key or anon_key
        if supabase_url and key_for_rest:
            headers = {
                'apikey': key_for_rest,
                'Authorization': f'Bearer {key_for_rest}',
                'Prefer': 'count=exact'
            }
            r = requests.get(f"{supabase_url.rstrip('/')}/rest/v1/users?select=*&limit=1", headers=headers, timeout=10)
            out['rest_status'] = r.status_code
        else:
            out['rest_exception'] = 'missing url or key'
    except Exception:
        out['rest_exception'] = traceback.format_exc()

    out['timestamp'] = __import__('datetime').datetime.utcnow().isoformat() + 'Z'

    return jsonify(out)


@test_bp.route('/clear_session')
def clear_session():
    """Clear server session and unset the session cookie to help break redirect loops."""
    try:
        session.clear()
    except Exception:
        pass
    resp = make_response(jsonify({'cleared': True, 'note': 'Session cleared; please clear cookies in browser if problem persists.'}))
    # Explicitly unset the Flask session cookie
    try:
        cookie_name = current_app.session_cookie_name
        resp.set_cookie(cookie_name, value='', expires=0, path='/')
    except Exception:
        pass
    return resp
