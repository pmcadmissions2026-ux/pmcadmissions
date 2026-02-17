from flask import Blueprint, render_template, jsonify, current_app
from database.supabase_config import db
from config import Config
import os
import requests

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
