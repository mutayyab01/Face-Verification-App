import os
import logging
from datetime import timedelta

class Config:
    # Database Configuration
    DB_SERVER = os.environ.get('DB_SERVER') 
    DB_NAME = os.environ.get('DB_NAME') 
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_DRIVER = os.environ.get('DB_DRIVER')

    @property
    def DATABASE_URI(self):
        return (
            f"DRIVER={self.DB_DRIVER};"
            f"SERVER={self.DB_SERVER};"
            f"DATABASE={self.DB_NAME};"
            f"UID={self.DB_USERNAME};"
            f"PWD={self.DB_PASSWORD};"
            "Encrypt=yes;TrustServerCertificate=yes"
        )

    def log_configuration(self, log_path='logs/config.txt'):
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'w') as f:
                f.write("Flask App Configuration\n")
                f.write("========================\n")
                for attr in self.__class__.__dict__:
                    if attr.isupper():
                        value = getattr(self, attr, 'Not Set')
                        f.write(f"{attr}: {value}\n")

                f.write("\n# DATABASE_URI is not printed for security reasons.\n")

        except Exception as e:
            logging.error(f"Failed to log configuration: {e}")

    # Security Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Application Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.txt')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

# Configuration selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
