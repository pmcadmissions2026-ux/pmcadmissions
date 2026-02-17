from flask import session, redirect, url_for
from functools import wraps
from database.models import UserModel

def login_required(f):
    """Decorator to require user login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If we have a user_id but the user no longer exists (stale cookie),
        # clear the session to avoid redirect loops and force a fresh login.
        if 'user_id' in session:
            try:
                user = UserModel.get_user_by_id(session['user_id'])
                if not user:
                    session.clear()
                    return redirect(url_for('auth.login'))
            except Exception:
                # On any error, clear session and require login
                session.clear()
                return redirect(url_for('auth.login'))

        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles: list):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('auth.login'))
            
            user_role = session.get('user_role')
            if user_role not in roles:
                return redirect(url_for('auth.unauthorized'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Get current logged-in user"""
    if 'user_id' in session:
        return UserModel.get_user_by_id(session['user_id'])
    return None

def get_current_user_role():
    """Get current user's role"""
    return session.get('user_role')
