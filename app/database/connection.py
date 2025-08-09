import pyodbc
import logging
from config import Config

logger = logging.getLogger(__name__)

class DatabaseManager:
    @staticmethod
    def get_connection():
        """Create database connection with error handling"""
        try:
            conn = pyodbc.connect(Config().DATABASE_URI)
            return conn
        except pyodbc.Error as e:
            logger.error(f"Database connection error: {e}")
            return None
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Execute query with proper error handling"""
        conn = None
        try:
            conn = DatabaseManager.get_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            
            if fetch_one:
                return cursor.fetchone()
            elif fetch_all:
                return cursor.fetchall()
            else:
                conn.commit()
                return True
                
        except pyodbc.Error as e:
            logger.error(f"Database query error: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    