from flask import Flask
from datetime import timedelta
from config import Config
import os
import logging

def create_app():
    app = Flask(__name__,template_folder='../templates',
    static_folder='../templates/static',        # <-- where the folder actually is
    static_url_path='/static' )
    
    # ---- Setup Logging for Werkzeug ----
    log_dir = 'logs'
    log_path = os.path.join(log_dir, 'werkzeug.txt')
    os.makedirs(log_dir, exist_ok=True)

    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.setLevel(logging.INFO)  # or DEBUG if you want more details

    file_handler = logging.FileHandler(log_path)
    file_handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)

    # Prevent duplicate handlers if reloaded
    if not werkzeug_logger.handlers:
        werkzeug_logger.addHandler(file_handler)



    
    app.config.from_object(Config)
    app.secret_key = Config.SECRET_KEY
    app.permanent_session_lifetime = timedelta(hours=2)
    
    config_instance = Config()
    config_instance.log_configuration()

    # Register blueprints
    from app.auth import auth_bp
    from app.admin import admin_bp
    from app.hr import hr_bp
    from app.employees import employees_bp
    from app.contractors import contractors_bp
    from app.users import users_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(employees_bp, url_prefix='/admin/employees')
    app.register_blueprint(contractors_bp, url_prefix='/admin/contractors')
    app.register_blueprint(hr_bp, url_prefix='/admin/hr')
    app.register_blueprint(users_bp, url_prefix='/admin/users')

    
    # Register error handlers
    from app.utils import register_error_handlers, inject_user_context
    register_error_handlers(app)
    app.context_processor(inject_user_context)
    
    # Main route
    from flask import session, redirect, url_for
    @app.route('/')
    def index():
        if 'user_id' in session and 'user_type' in session:
            user_type = session.get('user_type', '').lower().strip()
            if user_type == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user_type == 'hr':
                return redirect(url_for('hr.dashboard'))
        return redirect(url_for('auth.login'))
    
    return app