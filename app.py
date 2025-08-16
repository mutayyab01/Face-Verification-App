import logging
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import os
from app import create_app
from datetime import datetime

def setup_logging():
    """Setup comprehensive logging configuration"""
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Root logger config
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Console handler (optional)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(message)s'
    ))
    root_logger.addHandler(console_handler)

    # --- Page Access Logger ---
    page_logger = logging.getLogger('page_access')
    page_logger.setLevel(logging.INFO)
    page_handler = TimedRotatingFileHandler(
        'logs/page_access.txt',
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8',
        delay=True
    )
    page_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    page_logger.addHandler(page_handler)

    # --- Security Logger ---
    security_logger = logging.getLogger('security')
    security_logger.setLevel(logging.INFO)
    security_handler = RotatingFileHandler(
        'logs/security.txt', maxBytes=10*1024*1024, backupCount=10
    )
    security_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    ))
    security_logger.addHandler(security_handler)

    # --- Error Logger ---
    error_logger = logging.getLogger('app_errors')
    error_logger.setLevel(logging.ERROR)
    error_handler = RotatingFileHandler(
        'logs/errors.txt', maxBytes=10*1024*1024, backupCount=5
    )
    error_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
    ))
    error_logger.addHandler(error_handler)

    # --- Startup Logger ---
    startup_logger = logging.getLogger('app_startup')
    startup_handler = RotatingFileHandler(
        'logs/startup.txt', maxBytes=5*1024*1024, backupCount=3
    )
    startup_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s'
    ))
    startup_logger.addHandler(startup_handler)


if __name__ == '__main__':
    setup_logging()
    app = create_app()
    
    # Log startup
    logging.getLogger('app_startup').info(
        f"Flask application starting up at {datetime.now()}"
    )

    app.run(debug=True, host='0.0.0.0', port=5000)
