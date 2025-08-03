import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    
    # Database Configuration
    DB_SERVER = os.environ.get('DB_SERVER') 
    DB_NAME = os.environ.get('DB_NAME') 
    DB_USERNAME = os.environ.get('DB_USERNAME')
    DB_PASSWORD = os.environ.get('DB_PASSWORD')
    DB_DRIVER = os.environ.get('DB_DRIVER')
    
    @property
    def DATABASE_URI(self):
        return f"DRIVER={self.DB_DRIVER};SERVER={self.DB_SERVER};DATABASE={self.DB_NAME};UID={self.DB_USERNAME};PWD={self.DB_PASSWORD};Encrypt=yes;TrustServerCertificate=yes"