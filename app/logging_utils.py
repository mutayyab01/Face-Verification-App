# app/utils/logging_utils.py
import logging
import json
from datetime import datetime
from flask import request, session, g
from functools import wraps
import traceback

# Get specialized loggers
page_logger = logging.getLogger('page_access')
security_logger = logging.getLogger('security')
error_logger = logging.getLogger('app_errors')

def get_user_info():
    """Extract user information from session"""
    return {
        'user_id': session.get('user_id'),
        'user_type': session.get('user_type'),
        'username': session.get('email'),
        'employee_id': session.get('employee_id')
    }

def get_request_info():
    """Extract request information"""
    return {
        'ip_address': request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr),
        'user_agent': request.headers.get('User-Agent', 'Unknown'),
        'method': request.method,
        'url': request.url,
        'path': request.path,
        'referrer': request.referrer or 'Direct',
        'args': dict(request.args),
        'form_keys': list(request.form.keys()) if request.form else []
    }

def log_page_access(additional_info=None):
    """Log page access with comprehensive details"""
    try:
        user_info = get_user_info()
        request_info = get_request_info()
        
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'user_info': user_info,
            'request_info': request_info,
            'session_id': session.get('_permanent_session_id', 'No Session'),
            'additional_info': additional_info or {}
        }
        
        # Create readable log message
        log_message = (
            f"USER: {user_info['username']} ({user_info['user_type']}) | "
            f"ID: {user_info['user_id']} | "
            f"IP: {request_info['ip_address']} | "
            f"METHOD: {request_info['method']} | "
            f"PATH: {request_info['path']} | "
            f"ARGS: {request_info['args']} | "
            f"REFERRER: {request_info['referrer']}"
        )
        
        if additional_info:
            log_message += f" | EXTRA: {json.dumps(additional_info)}"
        
        page_logger.info(log_message)
        
    except Exception as e:
        error_logger.error(f"Failed to log page access: {str(e)}")

def log_security_event(event_type, details=None, severity='INFO'):
    """Log security-related events"""
    try:
        user_info = get_user_info()
        request_info = get_request_info()
        
        log_message = (
            f"SECURITY EVENT: {event_type} | "
            f"USER: {user_info['username']} ({user_info['user_id']}) | "
            f"IP: {request_info['ip_address']} | "
            f"PATH: {request_info['path']}"
        )
        
        if details:
            log_message += f" | DETAILS: {json.dumps(details)}"
        
        if severity.upper() == 'ERROR':
            security_logger.error(log_message)
        elif severity.upper() == 'WARNING':
            security_logger.warning(log_message)
        else:
            security_logger.info(log_message)
            
    except Exception as e:
        error_logger.error(f"Failed to log security event: {str(e)}")

def require_logging(additional_info=None):
    """Decorator to automatically log function access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Log before function execution
                extra_info = additional_info or {}
                extra_info['function'] = f.__name__
                extra_info['module'] = f.__module__
                
                log_page_access(extra_info)
                
                # Execute function
                result = f(*args, **kwargs)
                
                # Log successful execution
                extra_info['execution_status'] = 'success'
                
                return result
                
            except Exception as e:
                # Log error
                error_info = {
                    'function': f.__name__,
                    'module': f.__module__,
                    'error': str(e),
                    'traceback': traceback.format_exc()
                }
                
                error_logger.error(f"Function execution failed: {json.dumps(error_info)}")
                
                # Re-raise the exception
                raise
        
        return decorated_function
    return decorator

def log_api_call(endpoint, method, status_code, response_time=None):
    """Log API calls"""
    try:
        additional_info = {
            'api_endpoint': endpoint,
            'http_method': method,
            'status_code': status_code,
            'response_time_ms': response_time
        }
        
        log_page_access(additional_info)
        
    except Exception as e:
        error_logger.error(f"Failed to log API call: {str(e)}")
