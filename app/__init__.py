from flask import Flask, g, request, session,render_template
from datetime import timedelta
from config import Config
import os
import logging
import time

def create_app():
    app = Flask(__name__,
               template_folder='../templates',
               static_folder='../templates/static',
               static_url_path='/static')
    
    # ---- Setup Logging for Werkzeug ----
    log_dir = 'logs'
    log_path = os.path.join(log_dir, 'werkzeug.txt')
    os.makedirs(log_dir, exist_ok=True)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    if not werkzeug_logger.handlers:
        werkzeug_logger.addHandler(file_handler)

    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(hours=2)
    
    config_instance = Config()
    config_instance.log_configuration()

    # Import logging utilities
    from app.logging_utils import (
        log_page_access, 
        log_security_event, 
    )

    # Before request handler for logging
    @app.before_request
    def before_request():
        g.start_time = time.time()
        
        # Initialize tracking variables
        if not hasattr(g, 'request_count'):
            g.request_count = 0
        if not hasattr(g, 'unique_users'):
            g.unique_users = set()
        if not hasattr(g, 'top_pages'):
            g.top_pages = {}
        if not hasattr(g, 'error_count'):
            g.error_count = 0
        
        # Track this request
        g.request_count += 1
        
        # Track unique users
        user_id = session.get('user_id')
        if user_id:
            g.unique_users.add(user_id)
        
        # Track page visits
        page = request.path
        g.top_pages[page] = g.top_pages.get(page, 0) + 1
        
        # Skip logging for static files
        if request.path.startswith('/static/'):
            return
            
        # Log the page access
        additional_info = {
            'request_id': id(request),
            'content_type': request.headers.get('Content-Type', 'Unknown')
        }
        
        log_page_access(additional_info)

    # After request handler
    @app.after_request
    def after_request(response):
        # Skip for static files
        if request.path.startswith('/static/'):
            return response
            
        # Calculate response time
        response_time = None
        if hasattr(g, 'start_time'):
            response_time = round((time.time() - g.start_time) * 1000, 2)  # milliseconds
        
        # Log response information
        from app.logging_utils import log_api_call
        
        log_api_call(
            endpoint=request.endpoint or 'unknown',
            method=request.method,
            status_code=response.status_code,
            response_time=response_time
        )
        
        # Track errors
        if response.status_code >= 400:
            g.error_count += 1
            
        return response

    # Register blueprints with logging
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.hr import hr_bp
    from app.employees import employees_bp
    from app.contractors import contractors_bp
    from app.users import users_bp
    from app.finance import finance_bp
    from app.face import face_bp
     
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(finance_bp)
    app.register_blueprint(employees_bp, url_prefix='/admin/employees')
    app.register_blueprint(contractors_bp, url_prefix='/admin/contractors')    
    app.register_blueprint(users_bp, url_prefix='/admin/users')
    app.register_blueprint(face_bp)

    # Register error handlers
    from app.utils import register_error_handlers, inject_user_context
    register_error_handlers(app)
    app.context_processor(inject_user_context)
    
    # Main route with logging
    from flask import session, redirect, url_for
    @app.route('/')
    def index():
        from app.logging_utils import log_page_access
        
        if 'user_id' in session and 'user_type' in session:
            user_type = session.get('user_type', '').lower().strip()
            
            # Log the redirect decision
            log_page_access({
                'action': 'redirect_from_index',
                'target_user_type': user_type
            })
            
            if user_type == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user_type == 'hr':
                return redirect(url_for('hr.dashboard'))
            elif user_type == 'finance':
                return redirect(url_for('finance.dashboard'))
            elif user_type == 'cashier':
                return redirect(url_for('face.dashboard'))
        
        # Log unauthorized access attempt
        log_page_access({
            'action': 'redirect_to_login',
            'reason': 'no_valid_session'
        })
        
        return redirect(url_for('auth.login'))
    
    return app