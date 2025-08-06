from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from . import routes

# ========================================
# app/auth/decorators.py (Authentication Decorators)
# ========================================
from functools import wraps
from flask import session, request, redirect, url_for, flash, render_template
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.database import DatabaseManager
        from flask import current_app
        
        if 'user_id' not in session or 'user_type' not in session:
            logger.warning(f"Unauthorized access attempt to {request.endpoint}")
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        
        # Check session timeout
        if 'last_activity' in session:
            try:
                if isinstance(session['last_activity'], str):
                    last_activity = datetime.fromisoformat(session['last_activity'])
                else:
                    last_activity = session['last_activity']
                
                current_time = datetime.now()
                if hasattr(last_activity, 'tzinfo') and last_activity.tzinfo is not None:
                    last_activity = last_activity.replace(tzinfo=None)
                
                if current_time - last_activity > current_app.permanent_session_lifetime:
                    logger.info(f"Session expired for user {session.get('email')}")
                    session.clear()
                    flash('Session expired. Please log in again.', 'warning')
                    return redirect(url_for('auth.login'))
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing session timestamp: {e}")
                session['last_activity'] = datetime.now()
        
        session['last_activity'] = datetime.now()
        
        # Verify user still exists
        user = DatabaseManager.execute_query(
            "SELECT Id, Email, Type FROM [User] WHERE Id = ?",
            (session['user_id'],),
            fetch_one=True
        )
        
        if not user:
            logger.warning(f"User {session.get('email')} no longer exists in database")
            session.clear()
            flash('User account not found. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        
        session['user_type'] = user[2].lower().strip()
        session['email'] = user[1]
        
        return f(*args, **kwargs)
    return decorated_function

def require_role(allowed_roles):
    """Decorator to require specific roles"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or 'user_type' not in session:
                logger.warning(f"Unauthenticated access attempt to {request.endpoint}")
                return redirect(url_for('auth.login'))
            
            user_type = session['user_type'].lower().strip()
            normalized_roles = [role.lower().strip() for role in allowed_roles]
            
            if user_type not in normalized_roles:
                logger.warning(f"Access denied for user {session.get('email')} (type: '{user_type}') to {request.endpoint}")
                return render_template('errors/access_denied.html', 
                                     user_type=user_type, 
                                     required_roles=allowed_roles), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_role(required_roles):
    """Check if current user has required role"""
    if 'user_type' not in session:
        return False
    
    user_type = session['user_type'].lower().strip()
    normalized_roles = [role.lower().strip() for role in required_roles]
    return user_type in normalized_roles