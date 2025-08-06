from app.database import DatabaseManager
import logging

logger = logging.getLogger(__name__)

class UserModel:
    @staticmethod
    def get_all():
        """Get all users"""
        return DatabaseManager.execute_query(
            "SELECT Id, Email, Type FROM [User] ORDER BY Email",
            fetch_all=True
        )
    
    @staticmethod
    def get_by_email(email):
        """Get user by email"""
        return DatabaseManager.execute_query(
            "SELECT Id FROM [User] WHERE LOWER(TRIM(Email)) = ?",
            (email.lower().strip(),),
            fetch_one=True
        )
    
    @staticmethod
    def create(email, password, user_type):
        """Create new user"""
        return DatabaseManager.execute_query(
            "INSERT INTO [User] (Email, Password, Type) VALUES (?, ?, ?)",
            (email, password, user_type)
        )