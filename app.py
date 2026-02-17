from flask import Flask, render_template, request, session, redirect, url_for
from flask_session import Session
import tempfile
from config import config
import os

# Create Flask app
app = Flask(__name__)

# Load configuration
env = os.getenv('FLASK_ENV', 'development')
app.config.from_object(config[env])

# Initialize session
# Configure session storage. Prefer filesystem in a writable temp dir; if
# that's not possible (serverless/read-only), fall back to Flask's
# signed-cookie sessions by skipping Flask-Session initialization.
session_dir = os.environ.get('SESSION_FILE_DIR') or os.path.join(tempfile.gettempdir(), 'flask_session')
session_writable = False
try:
    os.makedirs(session_dir, exist_ok=True)
    testfile = os.path.join(session_dir, '.write_test')
    with open(testfile, 'w') as f:
        f.write('test')
    os.remove(testfile)
    session_writable = True
except Exception:
    session_writable = False

if session_writable:
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = session_dir
    Session(app)
else:
    # Use default client-side sessions (signed cookies). Log for visibility.
    print('Warning: session filesystem not writable; using client-side sessions')

# Register blueprints
from auth.routes import auth_bp
from admin.routes import admin_bp
# Test routes for quick Supabase checks
from test.routes import test_bp
# Student portal disabled - staff-only system
# from student.routes import student_bp

app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
# register test blueprint
app.register_blueprint(test_bp)
# app.register_blueprint(student_bp)

# ============================================
# ROUTES
# ============================================

@app.route('/')
def index():
    """Home page - redirect to login if not authenticated"""
    if 'user_id' in session:
        # Staff-only system - all users go to admin dashboard
        return redirect(url_for('admin.dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/health')
def health():
    """Health check endpoint"""
    return {'status': 'ok', 'message': 'PMC Admission Control System is running'}

# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('errors/500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return render_template('errors/403.html'), 403

# ============================================
# CONTEXT PROCESSORS
# ============================================

@app.context_processor
def inject_user():
    """Inject user info into templates"""
    user_data = None
    if 'user_id' in session:
        user_data = {
            'id': session.get('user_id'),
            'name': session.get('user_name'),
            'email': session.get('user_email', ''),
            'role': session.get('user_role')
        }
    
    return {
        'user': user_data,
        'user_name': session.get('user_name'),
        'user_role': session.get('user_role'),
        'is_authenticated': 'user_id' in session
    }

# ============================================
# MAIN ENTRY POINT
# ============================================

if __name__ == '__main__':
    # Create necessary directories. Use the system temp dir for session
    # storage in serverless (read-only) environments like Vercel.
    session_dir = os.environ.get('SESSION_FILE_DIR') or os.path.join(tempfile.gettempdir(), 'flask_session')
    try:
        os.makedirs(session_dir, exist_ok=True)
    except Exception:
        # If the runtime filesystem is read-only, fall back to not creating
        # the directory (Flask-Session will error if it cannot write). In
        # production it's preferable to use Redis or signed-cookie sessions.
        session_dir = None

    # Ensure templates/static folders exist locally (no-op on Vercel)
    try:
        os.makedirs('templates', exist_ok=True)
        os.makedirs('static', exist_ok=True)
    except Exception:
        pass
    
    # Print all registered routes
    print("\n" + "="*60)
    print("REGISTERED ROUTES:")
    print("="*60)
    for rule in app.url_map.iter_rules():
        if 'admin' in rule.rule or 'get-student' in rule.rule:
            methods = [m for m in rule.methods if m not in ('HEAD', 'OPTIONS')]
            methods_str = ', '.join(sorted(methods))
            print(f"{rule.rule} -> {rule.endpoint} [{methods_str}]")
    print("="*60 + "\n")
    
    # Configure filesystem session directory if available
    if session_dir:
        app.config['SESSION_FILE_DIR'] = session_dir

    # Run the application (use PORT from environment for hosting platforms)
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=app.config.get('DEBUG', False)
    )
