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
import json

logger = logging.getLogger(__name__)
auth_logger = logging.getLogger('auth')
security_logger = logging.getLogger('security')

def log_auth_event(event_type, user_info=None, additional_data=None, level='INFO'):
    """Helper function to log authentication events in single line format"""
    try:
        from app.logging_utils import get_request_info
        
        # Get request info
        request_info = get_request_info()
        
        # Prepare user information
        user_id = user_info.get('user_id', 'Unknown') if user_info else session.get('user_id', 'Unknown')
        email = user_info.get('email', 'Unknown') if user_info else session.get('email', 'Unknown')
        user_type = user_info.get('user_type', 'Unknown') if user_info else session.get('user_type', 'Unknown')
        
        # Create comprehensive single-line log message
        log_parts = [
            f"AUTH EVENT: {event_type}",
            f"USER: {email}",
            f"ID: {user_id}",
            f"TYPE: {user_type}",
            f"IP: {request_info.get('ip_address', 'Unknown')}",
            f"METHOD: {request.method if request else 'Unknown'}",
            f"PATH: {request_info.get('path', 'Unknown')}",
            f"ENDPOINT: {request.endpoint if request else 'Unknown'}",
            f"USER_AGENT: {request_info.get('user_agent', 'Unknown')[:50]}...",
            f"REFERRER: {request_info.get('referrer', 'Unknown')}",
            f"SESSION_ID: {session.get('_permanent_session_id', 'No Session')[:10]}...",
            f"TIMESTAMP: {datetime.now().isoformat()}"
        ]
        
        # Add additional data if provided
        if additional_data:
            for key, value in additional_data.items():
                if isinstance(value, (dict, list)):
                    log_parts.append(f"{key.upper()}: {json.dumps(value)}")
                else:
                    log_parts.append(f"{key.upper()}: {value}")
        
        # Join all parts with " | "
        log_message = " | ".join(log_parts)
        
        # Log at appropriate level
        if level.upper() == 'ERROR':
            auth_logger.error(log_message)
            security_logger.error(log_message)
        elif level.upper() == 'WARNING':
            auth_logger.warning(log_message)
            security_logger.warning(log_message)
        else:
            auth_logger.info(log_message)
            
    except Exception as e:
        logger.error(f"Failed to log auth event: {str(e)}")

def require_auth(f):
    """Decorator to require authentication with comprehensive logging"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.database import DatabaseManager
        from flask import current_app
        
        # Log access attempt
        log_auth_event('ACCESS_ATTEMPT', 
                      additional_data={
                          'function': f.__name__,
                          'has_session': 'user_id' in session
                      })
        
        if 'user_id' not in session or 'user_type' not in session:
            logger.warning(f"Unauthorized access attempt to {request.endpoint}")
            log_auth_event('ACCESS_DENIED', 
                          additional_data={
                              'reason': 'no_session_data',
                              'function': f.__name__,
                              'has_user_id': 'user_id' in session,
                              'has_user_type': 'user_type' in session,
                              'session_keys': list(session.keys())
                          },
                          level='WARNING')
            
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
                
                session_duration = current_time - last_activity
                session_timeout = current_app.permanent_session_lifetime
                
                if session_duration > session_timeout:
                    logger.info(f"Session expired for user {session.get('email')}")
                    log_auth_event('SESSION_EXPIRED',
                                  additional_data={
                                      'last_activity': last_activity.isoformat(),
                                      'session_duration_minutes': round(session_duration.total_seconds() / 60, 2),
                                      'session_timeout_minutes': round(session_timeout.total_seconds() / 60, 2),
                                      'function': f.__name__
                                  },
                                  level='INFO')
                    
                    session.clear()
                    flash('Session expired. Please log in again.', 'warning')
                    return redirect(url_for('auth.login'))
                    
            except (ValueError, TypeError) as e:
                logger.warning(f"Error parsing session timestamp: {e}")
                log_auth_event('SESSION_PARSING_ERROR',
                              additional_data={
                                  'error': str(e),
                                  'last_activity_type': type(session.get('last_activity')).__name__,
                                  'last_activity_value': str(session.get('last_activity')),
                                  'function': f.__name__
                              },
                              level='WARNING')
                
                session['last_activity'] = datetime.now()
        
        # Update last activity
        session['last_activity'] = datetime.now()
        
        # Verify user still exists
        try:
            user = DatabaseManager.execute_query(
                "SELECT Id, Email, Type FROM [User] WHERE Id = ?",
                (session['user_id'],),
                fetch_one=True
            )
            
            if not user:
                logger.warning(f"User {session.get('email')} no longer exists in database")
                log_auth_event('USER_NOT_FOUND',
                              additional_data={
                                  'function': f.__name__,
                                  'session_user_id': session.get('user_id'),
                                  'session_email': session.get('email')
                              },
                              level='WARNING')
                
                session.clear()
                flash('User account not found. Please log in again.', 'error')
                return redirect(url_for('auth.login'))
            
            # Update session with fresh data
            session['user_type'] = user[2].lower().strip()
            session['email'] = user[1]
            
            # Log successful authentication check
            log_auth_event('AUTH_SUCCESS',
                          user_info={
                              'user_id': user[0],
                              'email': user[1],
                              'user_type': user[2]
                          },
                          additional_data={
                              'function': f.__name__,
                              'session_updated': True
                          })
            
        except Exception as e:
            log_auth_event('DATABASE_ERROR',
                          additional_data={
                              'error': str(e),
                              'function': f.__name__,
                              'error_type': type(e).__name__
                          },
                          level='ERROR')
            
            flash('Authentication error. Please try again.', 'error')
            return redirect(url_for('auth.login'))
        
        return f(*args, **kwargs)
    return decorated_function

def require_role(allowed_roles):
    """Decorator to require specific roles with comprehensive logging"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_role = session.get('user_type', '').lower().strip()
            
            # Log role check attempt
            log_auth_event('ROLE_CHECK_ATTEMPT',
                          additional_data={
                              'function': f.__name__,
                              'required_roles': allowed_roles,
                              'current_role': current_role,
                              'has_session': 'user_id' in session
                          })
            
            if 'user_id' not in session or 'user_type' not in session:
                logger.warning(f"Unauthenticated access attempt to {request.endpoint}")
                log_auth_event('ROLE_CHECK_FAILED',
                              additional_data={
                                  'reason': 'no_session',
                                  'required_roles': allowed_roles,
                                  'function': f.__name__
                              },
                              level='WARNING')
                
                return redirect(url_for('auth.login'))
            
            normalized_roles = [role.lower().strip() for role in allowed_roles]
            
            if current_role not in normalized_roles:
                logger.warning(f"Access denied for user {session.get('email')} (type: '{user_type}') to {request.endpoint}")
                log_auth_event('ACCESS_DENIED_ROLE',
                              additional_data={
                                  'required_roles': allowed_roles,
                                  'normalized_required': normalized_roles,
                                  'current_role': current_role,
                                  'function': f.__name__,
                                  'access_denied_reason': 'insufficient_privileges'
                              },
                              level='WARNING')
                
                return render_template('errors/access_denied.html', 
                                     user_type=current_role, 
                                     required_roles=allowed_roles), 403
            
            # Log successful role check
            log_auth_event('ROLE_CHECK_SUCCESS',
                          additional_data={
                              'granted_role': current_role,
                              'required_roles': allowed_roles,
                              'function': f.__name__
                          })
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def has_role(required_roles):
    """Check if current user has required role with logging"""
    user_has_session = 'user_type' in session
    current_role = session.get('user_type', '').lower().strip() if user_has_session else None
    normalized_roles = [role.lower().strip() for role in required_roles]
    has_required_role = current_role in normalized_roles if current_role else False
    
    # Log role verification
    log_auth_event('ROLE_VERIFICATION',
                  additional_data={
                      'required_roles': required_roles,
                      'current_role': current_role,
                      'has_session': user_has_session,
                      'verification_result': has_required_role,
                      'normalized_roles': normalized_roles
                  })
    
    return has_required_role

# ========================================
# Specific Auth Event Logging Functions
# ========================================

def log_login_attempt(username, success=False, failure_reason=None, user_data=None):
    """Log login attempts with detailed information"""
    log_auth_event('LOGIN_ATTEMPT',
                  user_info=user_data,
                  additional_data={
                      'username': username,
                      'success': success,
                      'failure_reason': failure_reason,
                      'login_time': datetime.now().isoformat()
                  },
                  level='INFO' if success else 'WARNING')

def log_login_success(user_data):
    """Log successful login"""
    log_auth_event('LOGIN_SUCCESS',
                  user_info=user_data,
                  additional_data={
                      'login_time': datetime.now().isoformat(),
                      'session_created': True
                  })

def log_logout_event(user_info=None, session_data=None):
    """Log logout events with session information"""
    session_duration = calculate_session_duration()
    
    log_auth_event('LOGOUT',
                  user_info=user_info or {
                      'user_id': session.get('user_id'),
                      'email': session.get('email'),
                      'user_type': session.get('user_type')
                  },
                  additional_data={
                      'logout_time': datetime.now().isoformat(),
                      'session_duration_minutes': round(session_duration, 2),
                      'session_data_keys': list(session.keys()) if session_data else [],
                      'voluntary_logout': True
                  })


def log_suspicious_activity(activity_type, user_info=None, details=None, risk_level='MEDIUM'):
    """Log suspicious authentication activities"""
    log_auth_event('SUSPICIOUS_ACTIVITY',
                  user_info=user_info or {
                      'user_id': session.get('user_id'),
                      'email': session.get('email')
                  },
                  additional_data={
                      'activity_type': activity_type,
                      'risk_level': risk_level,
                      'details': details,
                      'detection_time': datetime.now().isoformat()
                  },
                  level='WARNING')

def log_failed_login_attempt(username, failure_reason, ip_address=None):
    """Log failed login attempts"""
    log_auth_event('LOGIN_FAILED',
                  additional_data={
                      'username': username,
                      'failure_reason': failure_reason,
                      'ip_address': ip_address or request.remote_addr,
                      'user_agent': request.headers.get('User-Agent', 'Unknown')[:100],
                      'attempt_time': datetime.now().isoformat()
                  },
                  level='WARNING')

def log_account_lockout(username, reason='too_many_failed_attempts'):
    """Log account lockout events"""
    log_auth_event('ACCOUNT_LOCKOUT',
                  additional_data={
                      'username': username,
                      'reason': reason,
                      'lockout_time': datetime.now().isoformat()
                  },
                  level='WARNING')

def calculate_session_duration():
    """Calculate current session duration in minutes"""
    try:
        if 'last_activity' in session:
            if isinstance(session['last_activity'], str):
                last_activity = datetime.fromisoformat(session['last_activity'])
            else:
                last_activity = session['last_activity']
            
            if hasattr(last_activity, 'tzinfo') and last_activity.tzinfo is not None:
                last_activity = last_activity.replace(tzinfo=None)
            
            duration = datetime.now() - last_activity
            return duration.total_seconds() / 60  # Return minutes
    except Exception as e:
        logger.error(f"Error calculating session duration: {e}")
    return 0